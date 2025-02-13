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

from itertools import islice

from gluonts_customized.dataset.artificial import constant_dataset
from gluonts_customized.mx import DeepAREstimator
from gluonts_customized.mx.distribution import StudentTOutput
from gluonts_customized.mx.trainer import Trainer
from gluonts_customized.mx.util import get_hybrid_forward_input_names

ds_info, train_ds, test_ds = constant_dataset()
freq = ds_info.metadata.freq
prediction_length = ds_info.prediction_length


def test_distribution():
    """
    Makes sure additional tensors can be accessed and have expected shapes.
    """
    prediction_length = ds_info.prediction_length

    # todo adapt loader to anomaly detection use-case
    batch_size = 2
    num_samples = 3

    estimator = DeepAREstimator(
        freq=freq,
        prediction_length=prediction_length,
        trainer=Trainer(epochs=2, num_batches_per_epoch=1),
        distr_output=StudentTOutput(),
        batch_size=batch_size,
    )

    train_output = estimator.train_model(train_ds, test_ds)

    training_data_loader = estimator.create_training_data_loader(
        estimator.create_transformation().apply(train_ds)
    )

    seq_len = 2 * ds_info.prediction_length

    for data_entry in islice(training_data_loader, 1):
        input_names = get_hybrid_forward_input_names(
            type(train_output.trained_net)
        )

        distr = train_output.trained_net.distribution(
            *[data_entry[k] for k in input_names]
        )

        assert distr.sample(num_samples).shape == (
            num_samples,
            batch_size,
            seq_len,
        )
