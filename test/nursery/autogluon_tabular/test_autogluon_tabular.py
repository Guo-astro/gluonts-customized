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

from typing import List, Optional

import pytest
import numpy as np
import pandas as pd
import tempfile
from pathlib import Path

from gluonts_customized.dataset.common import ListDataset
from gluonts_customized.dataset.util import to_pandas
from gluonts_customized.nursery.autogluon_tabular.predictor import get_features_dataframe
from gluonts_customized.nursery.autogluon_tabular import TabularEstimator
from gluonts_customized.model.predictor import Predictor
from gluonts_customized.time_feature import (
    TimeFeature,
    hour_of_day,
    day_of_week,
    month_of_year,
)


@pytest.mark.parametrize(
    "series, time_features, lag_indices, past_data, expected_df",
    [
        (
            pd.Series(
                np.arange(5),
                index=pd.period_range(
                    "2020-12-31 22:00:00", freq="H", periods=5
                ),
            ),
            [month_of_year, day_of_week, hour_of_day],
            [1, 2, 5],
            None,
            pd.DataFrame(
                {
                    "month_of_year": [0.5, 0.5, -0.5, -0.5, -0.5],
                    "day_of_week": [
                        0.0,
                        0.0,
                        4.0 / 6 - 0.5,
                        4.0 / 6 - 0.5,
                        4.0 / 6 - 0.5,
                    ],
                    "hour_of_day": [
                        22.0 / 23 - 0.5,
                        0.5,
                        -0.5,
                        1.0 / 23 - 0.5,
                        2.0 / 23 - 0.5,
                    ],
                    "lag_1": [np.nan, 0, 1, 2, 3],
                    "lag_2": [np.nan, np.nan, 0, 1, 2],
                    "lag_5": [np.nan, np.nan, np.nan, np.nan, np.nan],
                    "target": np.arange(5),
                },
                index=pd.period_range(
                    "2020-12-31 22:00:00", freq="H", periods=5
                ),
            ),
        ),
        (
            pd.Series(
                np.arange(5),
                index=pd.period_range(
                    "2020-12-31 22:00:00", freq="H", periods=5
                ),
            ),
            [month_of_year, day_of_week, hour_of_day],
            [1, 2, 5],
            pd.Series(
                np.arange(5),
                index=pd.period_range(
                    "2020-12-31 16:00:00", freq="H", periods=5
                ),
            ),
            pd.DataFrame(
                {
                    "month_of_year": [0.5, 0.5, -0.5, -0.5, -0.5],
                    "day_of_week": [
                        0.0,
                        0.0,
                        4.0 / 6 - 0.5,
                        4.0 / 6 - 0.5,
                        4.0 / 6 - 0.5,
                    ],
                    "hour_of_day": [
                        22.0 / 23 - 0.5,
                        0.5,
                        -0.5,
                        1.0 / 23 - 0.5,
                        2.0 / 23 - 0.5,
                    ],
                    "lag_1": [np.nan, 0, 1, 2, 3],
                    "lag_2": [4, np.nan, 0, 1, 2],
                    "lag_5": [1, 2, 3, 4, np.nan],
                    "target": np.arange(5),
                },
                index=pd.period_range(
                    "2020-12-31 22:00:00", freq="H", periods=5
                ),
            ),
        ),
    ],
)
def test_get_features_dataframe(
    series: pd.Series,
    time_features: List[TimeFeature],
    lag_indices: List[int],
    past_data: Optional[pd.Series],
    expected_df: pd.DataFrame,
):
    got_df = get_features_dataframe(
        series,
        time_features=time_features,
        lag_indices=lag_indices,
        past_data=past_data,
    )
    pd.testing.assert_frame_equal(expected_df, got_df)


@pytest.mark.parametrize(
    "dataset, freq, prediction_length",
    [
        (
            ListDataset(
                [
                    {
                        "start": "1750-01-07 00:00:00",
                        "target": np.array(
                            [
                                1089.2,
                                1078.91,
                                1099.88,
                                35790.55,
                                34096.95,
                                34906.95,
                            ],
                        ),
                    },
                    {
                        "start": "1750-01-07 00:00:00",
                        "target": np.array(
                            [
                                1099.2,
                                1098.91,
                                1069.88,
                                35990.55,
                                34076.95,
                                34766.95,
                            ],
                        ),
                    },
                ],
                freq="W-TUE",
            ),
            "W-TUE",
            2,
        )
    ],
)
@pytest.mark.parametrize("lag_indices", [[], [1, 2, 5]])
@pytest.mark.parametrize("disable_auto_regression", [False, True])
@pytest.mark.parametrize(
    "validation_data",
    [
        None,
        ListDataset(
            [
                {
                    "start": "1750-01-07 00:00:00",
                    "target": np.array(
                        [
                            1089.2,
                            1078.91,
                            1099.88,
                            35790.55,
                            34096.95,
                            34906.95,
                        ],
                    ),
                },
                {
                    "start": "1750-01-07 00:00:00",
                    "target": np.array(
                        [
                            1099.2,
                            1098.91,
                            1069.88,
                            35990.55,
                            34076.95,
                            34766.95,
                        ],
                    ),
                },
            ],
            freq="W-TUE",
        ),
    ],
)
@pytest.mark.parametrize("last_k_for_val", [None, 2])
def test_tabular_estimator(
    dataset,
    freq,
    prediction_length: int,
    lag_indices: List[int],
    disable_auto_regression: bool,
    last_k_for_val: int,
    validation_data: ListDataset,
):
    estimator = TabularEstimator(
        freq=freq,
        prediction_length=prediction_length,
        lag_indices=lag_indices,
        time_limit=10,
        disable_auto_regression=disable_auto_regression,
        last_k_for_val=last_k_for_val,
    )

    def check_consistency(entry, f1, f2):
        ts = to_pandas(entry)
        start_timestamp = ts.index[-1] + 1
        assert f1.samples.shape == (1, prediction_length)
        assert f1.start_date == start_timestamp
        assert f2.samples.shape == (1, prediction_length)
        assert f2.start_date == start_timestamp
        assert np.allclose(f1.samples, f2.samples)

    with tempfile.TemporaryDirectory() as path:
        predictor = estimator.train(dataset, validation_data=validation_data)
        predictor.serialize(Path(path))
        predictor = None
        predictor = Predictor.deserialize(Path(path))
        assert not predictor.auto_regression or any(
            l < prediction_length for l in predictor.lag_indices
        )

        assert predictor.batch_size > 1

        forecasts_serial = list(predictor._predict_serial(dataset))
        forecasts_batch = list(predictor.predict(dataset))

        for entry, f1, f2 in zip(dataset, forecasts_serial, forecasts_batch):
            check_consistency(entry, f1, f2)

        if not predictor.auto_regression:
            forecasts_batch_autoreg = list(
                predictor._predict_batch_autoreg(dataset)
            )
            for entry, f1, f2 in zip(
                dataset, forecasts_serial, forecasts_batch_autoreg
            ):
                check_consistency(entry, f1, f2)
