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
import pytest

from gluonts_customized.evaluation.metrics import (
    abs_error,
    abs_target_mean,
    abs_target_sum,
    calculate_seasonal_error,
    coverage,
    mape,
    mase,
    mse,
    msis,
    quantile_loss,
    smape,
)

ZEROES = np.array([0.0] * 5)
LINEAR = np.array([0.0, 0.1, 0.2, 0.3, 0.4])
EXPONENTIAL = np.array([0.1, 0.01, 0.001, 0.0001, 0.00001])
CONSTANT = np.array([0.4] * 5)


# TODO remove `"exclude_zero_denominator": True` when metrics are refactored
@pytest.mark.parametrize(
    "target, forecast, metrics",
    [
        (
            ZEROES,
            ZEROES,
            [
                (mase, np.nan, {"seasonal_error": 0.0}),
                (mase, 0.0, {"seasonal_error": 1.0}),
                (mse, 0.0, {}),
                (abs_error, 0.0, {}),
                (quantile_loss, 0.0, {"q": 0.5}),
                (coverage, 1.0, {}),
                (mape, np.nan, {}),
                (smape, np.nan, {}),
            ],
        ),
        (
            LINEAR,
            ZEROES,
            [
                (mase, 0.2 / 10e-10, {"seasonal_error": 10e-10}),
                (mase, np.inf, {"seasonal_error": 0.0}),
                (mse, 0.06, {}),
                (abs_error, 1.0, {}),
                (quantile_loss, 0.2, {"q": 0.1}),
                (quantile_loss, 1.0, {"q": 0.5}),
                (quantile_loss, 1.8, {"q": 0.9}),
                (coverage, 0.2, {}),
                (mape, np.nan, {}),
                (smape, np.nan, {}),
            ],
        ),
        (
            LINEAR,
            CONSTANT,
            [
                (mase, 0.2, {"seasonal_error": 1}),
                (mse, 0.06, {}),
                (abs_error, 1.0, {}),
                (quantile_loss, 1.8, {"q": 0.1}),
                (quantile_loss, 1.0, {"q": 0.5}),
                (quantile_loss, 0.2, {"q": 0.9}),
                (coverage, 1.0, {}),
                (mape, np.inf, {}),
                (smape, 0.8304761904761906, {}),
            ],
        ),
        (
            ZEROES,
            EXPONENTIAL,
            [
                (mase, 0.022222, {"seasonal_error": 1}),
                (mse, 0.00202020202, {}),
                (abs_error, 0.11111, {}),
                (quantile_loss, 0.199998, {"q": 0.1}),
                (quantile_loss, 0.11111, {"q": 0.5}),
                (quantile_loss, 0.0222219, {"q": 0.9}),
                (coverage, 1.0, {}),
                (mape, np.inf, {}),
                (smape, 2.0, {}),
            ],
        ),
        (
            np.array([1.0, 2.0, 3.0, 0.0, 0.0]),
            np.array([2.0, 3.0, 4.0, 1.0, 0.0]),
            [
                (
                    mase,
                    0.8,
                    {"seasonal_error": 1},
                ),
                (mse, 0.8, {}),
                (abs_error, 4.0, {}),
                (quantile_loss, 7.2, {"q": 0.1}),
                (quantile_loss, 4.0, {"q": 0.5}),
                (quantile_loss, 0.7999999, {"q": 0.9}),
                (coverage, 1.0, {}),
                (mape, np.nan, {}),
                (smape, np.nan, {}),
            ],
        ),
        (
            CONSTANT,
            EXPONENTIAL,
            [
                (
                    mase,
                    0.377778,
                    {"seasonal_error": 1},
                ),
                (mse, 0.14424260202, {}),
                (abs_error, 1.88889, {}),
                (quantile_loss, 0.377778, {"q": 0.1}),
                (quantile_loss, 1.88889, {"q": 0.5}),
                (quantile_loss, 3.400002, {"q": 0.9}),
                (coverage, 0.0, {}),
                (mape, 0.944445, {}),
                (smape, 1.8182728, {}),
            ],
        ),
    ],
)
def test_metrics(target, forecast, metrics):
    for metric, expected, kwargs in metrics:
        np.testing.assert_almost_equal(
            metric(target, forecast, **kwargs), expected
        )


@pytest.mark.parametrize(
    "target, metric, expected",
    [
        (ZEROES, abs_target_sum, 0.0),
        (LINEAR, abs_target_sum, 1.0),
        (ZEROES, abs_target_mean, 0.0),
        (LINEAR, abs_target_mean, 0.2),
    ],
)
def test_target_metrics(target, metric, expected):
    np.testing.assert_almost_equal(metric(target), expected)


@pytest.mark.parametrize(
    "target, lower_quantile, upper_quantile, seasonal_error, alpha, expected",
    [
        (LINEAR, ZEROES, CONSTANT, 0.0, 0.05, np.inf),
        (LINEAR, ZEROES, CONSTANT, 1.0, 0.05, 0.4),
        (LINEAR, ZEROES, CONSTANT, 0.01, 0.05, 40.0),
        (ZEROES, ZEROES, ZEROES, 0.0, 0.05, np.nan),
    ],
)
def test_msis(
    target, lower_quantile, upper_quantile, seasonal_error, alpha, expected
):
    np.testing.assert_almost_equal(
        msis(
            target=target,
            lower_quantile=lower_quantile,
            upper_quantile=upper_quantile,
            seasonal_error=seasonal_error,
            alpha=alpha,
        ),
        expected,
    )


@pytest.mark.parametrize(
    "past_data, seasonality, expected",
    [
        (LINEAR, 1, 0.1),
        (LINEAR, 2, 0.2),
        (LINEAR, 3, 0.3),
        (LINEAR, 4, 0.4),
        (LINEAR, len(LINEAR), 0.1),
        (CONSTANT, 2, 0.0),
        (ZEROES, 1, 0.0),
        (EXPONENTIAL, 3, 0.054945),
    ],
)
def test_seasonal_error(past_data, seasonality, expected):
    np.testing.assert_almost_equal(
        calculate_seasonal_error(
            past_data=past_data, freq=None, seasonality=seasonality
        ),
        expected,
    )
