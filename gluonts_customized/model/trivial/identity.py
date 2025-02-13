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

import numpy as np

from gluonts_customized.core.component import validated
from gluonts_customized.dataset.common import DataEntry
from gluonts_customized.dataset.field_names import FieldName
from gluonts_customized.dataset.util import forecast_start
from gluonts_customized.model.forecast import Forecast, SampleForecast
from gluonts_customized.model.predictor import RepresentablePredictor


class IdentityPredictor(RepresentablePredictor):
    """
    A `Predictor` that uses the last `prediction_length` observations to
    predict the future.

    Parameters
    ----------
    prediction_length
        Prediction horizon.
    num_samples
        Number of samples to include in the forecasts. Not that the samples
        produced by this predictor will all be identical.
    """

    @validated()
    def __init__(self, prediction_length: int, num_samples: int) -> None:
        super().__init__(prediction_length=prediction_length)

        assert num_samples > 0, "The value of `num_samples` should be > 0"

        self.num_samples = num_samples

    def predict_item(self, item: DataEntry) -> Forecast:
        prediction = item["target"][-self.prediction_length :]
        samples = np.broadcast_to(
            array=np.expand_dims(prediction, 0),
            shape=(self.num_samples, self.prediction_length),
        )

        return SampleForecast(
            samples=samples,
            start_date=forecast_start(item),
            item_id=item.get(FieldName.ITEM_ID),
        )
