# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the "license" file accompanying this file. This file is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied. See the License for the specific language governing
# permissions and limitations under the License.

from functools import partial
from typing import List, Optional

from mxnet.gluon import HybridBlock

from gluonts_customized.core.component import validated
from gluonts_customized.dataset.common import Dataset
from gluonts_customized.dataset.field_names import FieldName
from gluonts_customized.dataset.loader import (
    DataLoader,
    TrainDataLoader,
    ValidationDataLoader,
)
from gluonts_customized.model.forecast_generator import QuantileForecastGenerator
from gluonts_customized.mx.batchify import batchify
from gluonts_customized.mx.model.estimator import GluonEstimator
from gluonts_customized.mx.model.predictor import RepresentableBlockPredictor
from gluonts_customized.mx.trainer import Trainer
from gluonts_customized.mx.util import copy_parameters, get_hybrid_forward_input_names
from gluonts_customized.time_feature import TimeFeature, time_features_from_frequency_str
from gluonts_customized.transform import (
    AddAgeFeature,
    AddObservedValuesIndicator,
    AddTimeFeatures,
    AsNumpyArray,
    Chain,
    ExpectedNumInstanceSampler,
    InstanceSampler,
    InstanceSplitter,
    SelectFields,
    SetField,
    TestSplitSampler,
    Transformation,
    ValidationSplitSampler,
    VstackFeatures,
)

# Relative import
from ._network import (
    SelfAttentionPredictionNetwork,
    SelfAttentionTrainingNetwork,
)


class SelfAttentionEstimator(GluonEstimator):
    @validated()
    def __init__(
        self,
        freq: str,
        prediction_length: int,
        cardinalities: List[int] = [],
        context_length: Optional[int] = None,
        trainer: Trainer = Trainer(),
        model_dim: int = 64,
        ffn_dim_multiplier: int = 2,
        num_heads: int = 4,
        num_layers: int = 3,
        num_outputs: int = 3,
        kernel_sizes: List[int] = [3, 5, 7, 9],
        distance_encoding: Optional[str] = "dot",
        pre_layer_norm: bool = False,
        dropout: float = 0.1,
        temperature: float = 1.0,
        time_features: Optional[List[TimeFeature]] = None,
        use_feat_dynamic_real: bool = True,
        use_feat_dynamic_cat: bool = False,
        use_feat_static_real: bool = False,
        use_feat_static_cat: bool = True,
        train_sampler: Optional[InstanceSampler] = None,
        validation_sampler: Optional[InstanceSampler] = None,
        batch_size: int = 32,
    ):
        super().__init__(trainer=trainer, batch_size=batch_size)

        self.prediction_length = prediction_length
        self.context_length = context_length or prediction_length
        self.model_dim = model_dim
        self.ffn_dim_multiplier = ffn_dim_multiplier
        self.num_heads = num_heads
        self.num_layers = num_layers
        self.num_outputs = num_outputs
        self.cardinalities = cardinalities
        self.kernel_sizes = kernel_sizes
        self.distance_encoding = distance_encoding
        self.pre_layer_norm = pre_layer_norm
        self.dropout = dropout
        self.temperature = temperature

        self.time_features = time_features or time_features_from_frequency_str(
            freq
        )
        self.use_feat_dynamic_cat = use_feat_dynamic_cat
        self.use_feat_dynamic_real = use_feat_dynamic_real
        self.use_feat_static_cat = use_feat_static_cat
        self.use_feat_static_real = use_feat_static_real
        self.train_sampler = (
            train_sampler
            if train_sampler is not None
            else ExpectedNumInstanceSampler(
                num_instances=1.0, min_future=prediction_length
            )
        )
        self.validation_sampler = (
            validation_sampler
            if validation_sampler is not None
            else ValidationSplitSampler(min_future=prediction_length)
        )

    def create_transformation(self) -> Transformation:
        transforms = []
        if self.use_feat_dynamic_real:
            transforms.append(
                AsNumpyArray(
                    field=FieldName.FEAT_DYNAMIC_REAL,
                    expected_ndim=2,
                )
            )
        else:
            transforms.extend(
                [
                    SetField(
                        output_field=FieldName.FEAT_DYNAMIC_REAL,
                        value=[[]]
                        * (self.context_length + self.prediction_length),
                    ),
                    AsNumpyArray(
                        field=FieldName.FEAT_DYNAMIC_REAL,
                        expected_ndim=2,
                    ),
                    # SwapAxes(input_fields=
                    # [FieldName.FEAT_DYNAMIC_REAL], axes=(0,1)),
                ]
            )
        if self.use_feat_dynamic_cat:
            transforms.append(
                AsNumpyArray(
                    field=FieldName.FEAT_DYNAMIC_CAT,
                    expected_ndim=2,
                )
            )
        else:
            # Manually set dummy dynamic categorical features and split by time
            # Unknown issue in dataloader if leave splitting to
            # InstanceSplitter
            transforms.extend(
                [
                    SetField(
                        output_field="past_" + FieldName.FEAT_DYNAMIC_CAT,
                        value=[[]] * self.context_length,
                    ),
                    AsNumpyArray(
                        field="past_" + FieldName.FEAT_DYNAMIC_CAT,
                        expected_ndim=2,
                    ),
                    SetField(
                        output_field="future_" + FieldName.FEAT_DYNAMIC_CAT,
                        value=[[]] * self.prediction_length,
                    ),
                    AsNumpyArray(
                        field="future_" + FieldName.FEAT_DYNAMIC_CAT,
                        expected_ndim=2,
                    ),
                ]
            )
        if self.use_feat_static_real:
            transforms.append(
                AsNumpyArray(
                    field=FieldName.FEAT_STATIC_REAL,
                    expected_ndim=1,
                )
            )
        else:
            transforms.extend(
                [
                    SetField(
                        output_field=FieldName.FEAT_STATIC_REAL,
                        value=[],
                    ),
                    AsNumpyArray(
                        field=FieldName.FEAT_STATIC_REAL,
                        expected_ndim=1,
                    ),
                ]
            )
        if self.use_feat_static_cat:
            transforms.append(
                AsNumpyArray(
                    field=FieldName.FEAT_STATIC_CAT,
                    expected_ndim=1,
                )
            )

        transforms.extend(
            [
                AsNumpyArray(field=FieldName.TARGET, expected_ndim=1),
                AddObservedValuesIndicator(
                    target_field=FieldName.TARGET,
                    output_field=FieldName.OBSERVED_VALUES,
                ),
                AddTimeFeatures(
                    start_field=FieldName.START,
                    target_field=FieldName.TARGET,
                    output_field=FieldName.FEAT_TIME,
                    time_features=self.time_features,
                    pred_length=self.prediction_length,
                ),
                AddAgeFeature(
                    target_field=FieldName.TARGET,
                    output_field=FieldName.FEAT_AGE,
                    pred_length=self.prediction_length,
                    log_scale=True,
                ),
                VstackFeatures(
                    output_field=FieldName.FEAT_DYNAMIC_REAL,
                    input_fields=[FieldName.FEAT_TIME, FieldName.FEAT_AGE]
                    + (
                        [FieldName.FEAT_DYNAMIC_REAL]
                        if self.use_feat_dynamic_real
                        else []
                    ),
                ),
            ]
        )
        return Chain(transforms)

    def _create_instance_splitter(self, mode: str):
        assert mode in ["training", "validation", "test"]

        instance_sampler = {
            "training": self.train_sampler,
            "validation": self.validation_sampler,
            "test": TestSplitSampler(),
        }[mode]

        time_series_fields = [FieldName.OBSERVED_VALUES]
        if self.use_feat_dynamic_cat:
            time_series_fields.append(FieldName.FEAT_DYNAMIC_CAT)
        if self.use_feat_dynamic_real or (self.time_features is not None):
            time_series_fields.append(FieldName.FEAT_DYNAMIC_REAL)

        return InstanceSplitter(
            target_field=FieldName.TARGET,
            is_pad_field=FieldName.IS_PAD,
            start_field=FieldName.START,
            forecast_start_field=FieldName.FORECAST_START,
            instance_sampler=instance_sampler,
            past_length=self.context_length,
            future_length=self.prediction_length,
            time_series_fields=time_series_fields,
        )

    def create_training_data_loader(
        self,
        data: Dataset,
        **kwargs,
    ) -> DataLoader:
        input_names = get_hybrid_forward_input_names(
            SelfAttentionTrainingNetwork
        )
        instance_splitter = self._create_instance_splitter("training")
        return TrainDataLoader(
            dataset=data,
            transform=instance_splitter + SelectFields(input_names),
            batch_size=self.batch_size,
            stack_fn=partial(batchify, ctx=self.trainer.ctx, dtype=self.dtype),
            **kwargs,
        )

    def create_validation_data_loader(
        self,
        data: Dataset,
        **kwargs,
    ) -> DataLoader:
        input_names = get_hybrid_forward_input_names(
            SelfAttentionTrainingNetwork
        )
        instance_splitter = self._create_instance_splitter("validation")
        return ValidationDataLoader(
            dataset=data,
            transform=instance_splitter + SelectFields(input_names),
            batch_size=self.batch_size,
            stack_fn=partial(batchify, ctx=self.trainer.ctx, dtype=self.dtype),
        )

    def create_training_network(self) -> SelfAttentionTrainingNetwork:
        return SelfAttentionTrainingNetwork(
            context_length=self.context_length,
            prediction_length=self.prediction_length,
            d_hidden=self.model_dim,
            m_ffn=self.ffn_dim_multiplier,
            n_head=self.num_heads,
            n_layers=self.num_layers,
            n_output=self.num_outputs,
            cardinalities=self.cardinalities,
            kernel_sizes=self.kernel_sizes,
            dist_enc=self.distance_encoding,
            pre_ln=self.pre_layer_norm,
            dropout=self.dropout,
            temperature=self.temperature,
        )

    def create_predictor(
        self, transformation: Transformation, trained_network: HybridBlock
    ) -> RepresentableBlockPredictor:
        prediction_splitter = self._create_instance_splitter("test")

        prediction_network = SelfAttentionPredictionNetwork(
            context_length=self.context_length,
            prediction_length=self.prediction_length,
            d_hidden=self.model_dim,
            m_ffn=self.ffn_dim_multiplier,
            n_head=self.num_heads,
            n_layers=self.num_layers,
            n_output=self.num_outputs,
            cardinalities=self.cardinalities,
            kernel_sizes=self.kernel_sizes,
            dist_enc=self.distance_encoding,
            pre_ln=self.pre_layer_norm,
            dropout=self.dropout,
            temperature=self.temperature,
        )
        copy_parameters(trained_network, prediction_network)
        return RepresentableBlockPredictor(
            input_transform=transformation + prediction_splitter,
            prediction_net=prediction_network,
            batch_size=self.batch_size,
            prediction_length=self.prediction_length,
            ctx=self.trainer.ctx,
            forecast_generator=QuantileForecastGenerator(
                quantiles=[str(q) for q in prediction_network.quantiles],
            ),
        )
