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

from typing import Callable, Union

import numpy as np

from gluonts_customized.core.component import validated
from gluonts_customized.dataset.common import DataEntry
from gluonts_customized.dataset.util import forecast_start
from gluonts_customized.dataset.field_names import FieldName
from gluonts_customized.model.forecast import Forecast, SampleForecast
from gluonts_customized.model.predictor import RepresentablePredictor
from gluonts_customized.transform.feature import (
    LastValueImputation,
    MissingValueImputation,
)


class SeasonalNaivePredictor(RepresentablePredictor):
    """
    Seasonal naïve forecaster.

    For each time series :math:`y`, this predictor produces a forecast
    :math:`\\tilde{y}(T+k) = y(T+k-h)`, where :math:`T` is the forecast time,
    :math:`k = 0, ...,` `prediction_length - 1`, and :math:`h =`
    `season_length`.

    If `prediction_length > season_length`, then the season is repeated
    multiple times. If a time series is shorter than season_length, then the
    mean observed value is used as prediction.

    Parameters
    ----------
    prediction_length
        Number of time points to predict.
    season_length
        Seasonality used to make predictions. If this is an integer, then a fixed
        sesasonlity is applied; if this is a function, then it will be called on each
        given entry's ``freq`` attribute of the ``"start"`` field, and will return
        the seasonality to use.
    imputation_method
        The imputation method to use in case of missing values.
        Defaults to :py:class:`LastValueImputation` which replaces each missing
        value with the last value that was not missing.
    """

    @validated()
    def __init__(
        self,
        prediction_length: int,
        season_length: Union[int, Callable],
        imputation_method: MissingValueImputation = LastValueImputation(),
    ) -> None:
        super().__init__(prediction_length=prediction_length)

        assert (
            not isinstance(season_length, int) or season_length > 0
        ), "The value of `season_length` should be > 0"

        self.prediction_length = prediction_length
        self.season_length = season_length
        self.imputation_method = imputation_method

    def predict_item(self, item: DataEntry) -> Forecast:
        if isinstance(self.season_length, int):
            season_length = self.season_length
        else:
            season_length = self.season_length(item["start"].freq)

        target = np.asarray(item[FieldName.TARGET], np.float32)
        len_ts = len(target)
        forecast_start_time = forecast_start(item)

        assert (
            len_ts >= 1
        ), "all time series should have at least one data point"

        if np.isnan(target).any():
            target = target.copy()
            target = self.imputation_method(target)

        if len_ts >= season_length:
            indices = [
                len_ts - season_length + k % season_length
                for k in range(self.prediction_length)
            ]
            samples = target[indices].reshape((1, self.prediction_length))
        else:
            samples = np.full(
                shape=(1, self.prediction_length),
                fill_value=np.nanmean(target),
            )

        return SampleForecast(
            samples=samples,
            start_date=forecast_start_time,
            item_id=item.get("item_id", None),
            info=item.get("info", None),
        )
