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

"""
Test the lags computed for different frequencies.
"""

import pytest

import gluonts_customized.time_feature.lag as date_feature_set

from .common import H, M, Q, Y

# These are the expected lags for common frequencies and corner cases.
# By default all frequencies have the following lags: [1, 2, 3, 4, 5, 6, 7].
# Remaining lags correspond to the same `season` (+/- `delta`) in previous `k` cycles.
EXPECTED_LAGS = {
    # (apart from the default lags) centered around each of the last 3 hours (delta = 2)
    "4S": [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        13,
        14,
        15,
        16,
        17,
        28,
        29,
        30,
        31,
        32,
        43,
        44,
        45,
        46,
        47,
        898,
        899,
        900,
        901,
        902,
    ],
    "min": [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        58,
        59,
        60,
        61,
        62,
        118,
        119,
        120,
        121,
        122,
        178,
        179,
        180,
        181,
        182,
    ],
    # centered around each of the last 3 hours (delta = 2) + last 7 days (delta = 1)
    "15min": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
    + [
        95,
        96,
        97,
        191,
        192,
        193,
        287,
        288,
        289,
        383,
        384,
        385,
        479,
        480,
        481,
        575,
        576,
        577,
        671,
        672,
        673,
    ],
    # centered around each of the last 3 hours (delta = 2) + last 7 days (delta = 1) + 3 weeks (delta = 1)
    "30min": [1, 2, 3, 4, 5, 6, 7, 8]
    + [
        47,
        48,
        49,
        95,
        96,
        97,
        143,
        144,
        145,
        191,
        192,
        193,
        239,
        240,
        241,
        287,
        288,
        289,
        335,
        336,
        337,
    ]
    + [671, 672, 673, 1007, 1008, 1009],
    # centered around each of the last 3 hours (delta = 2) + last 7 days (delta = 1) + last 6 weeks (delta = 1)
    "59min": [1, 2, 3, 4, 5, 6, 7]
    + [
        23,
        24,
        25,
        47,
        48,
        49,
        72,
        73,
        74,
        96,
        97,
        98,
        121,
        122,
        123,
        145,
        146,
        147,
        169,
        170,
        171,
    ]
    + [340, 341, 342, 511, 512, 513, 682, 683, 684, 731, 732, 733],
    # centered around each of the last 3 hours (delta = 2) + last 7 days (delta = 1) + last 6 weeks (delta = 1)
    "61min": [1, 2, 3, 4, 5, 6, 7]
    + [
        22,
        23,
        24,
        46,
        47,
        48,
        69,
        70,
        71,
        93,
        94,
        95,
        117,
        118,
        119,
        140,
        141,
        142,
        164,
        165,
        166,
    ]
    + [329, 330, 331, 494, 495, 496, 659, 660, 661, 707, 708, 709],
    # centered around each of the last 3 hours (delta = 2) + last 7 days (delta = 1) + last 6 weeks (delta = 1)
    H: [1, 2, 3, 4, 5, 6, 7]
    + [
        23,
        24,
        25,
        47,
        48,
        49,
        71,
        72,
        73,
        95,
        96,
        97,
        119,
        120,
        121,
        143,
        144,
        145,
        167,
        168,
        169,
    ]
    + [335, 336, 337, 503, 504, 505, 671, 672, 673, 719, 720, 721],
    # centered around each of the last 7 days (delta = 1) + last 4 weeks (delta = 1) + last 1 month (delta = 1) +
    #  last 8th and 12th weeks (delta = 0)
    ("6" + H): [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        11,
        12,
        13,
        15,
        16,
        17,
        19,
        20,
        21,
        23,
        24,
        25,
        27,
        28,
        29,
    ]
    + [55, 56, 57, 83, 84, 85, 111, 112, 113]
    + [119, 120, 121]
    + [224, 336],
    # centered around each of the last 7 days (delta = 1) + last 4 weeks (delta = 1) + last 1 month (delta = 1) +
    #  last 8th and 12th weeks (delta = 0) + last year (delta = 1)
    ("12" + H): [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    + [27, 28, 29, 41, 42, 43, 55, 56, 57]
    + [59, 60, 61]
    + [112, 168]
    + [727, 728, 729],
    # centered around each of the last 7 days (delta = 1) + last 4 weeks (delta = 1) + last 1 month (delta = 1) +
    #  last 8th and 12th weeks (delta = 0) + last 3 years (delta = 1)
    ("23" + H): [1, 2, 3, 4, 5, 6, 7, 8]
    + [13, 14, 15, 20, 21, 22, 28, 29]
    + [30, 31, 32]
    + [58, 87]
    + [378, 379, 380, 758, 759, 760, 1138, 1139, 1140],
    # centered around each of the last 7 days (delta = 1) + last 4 weeks (delta = 1) + last 1 month (delta = 1) +
    #  last 8th and 12th weeks (delta = 0) + last 3 years (delta = 1)
    ("25" + H): [1, 2, 3, 4, 5, 6, 7]
    + [12, 13, 14, 19, 20, 21, 25, 26, 27]
    + [28, 29]
    + [53, 80]
    + [348, 349, 350, 697, 698, 699, 1047, 1048, 1049],
    # centered around each of the last 7 days (delta = 1) + last 4 weeks (delta = 1) + last 1 month (delta = 1) +
    #  last 8th and 12th weeks (delta = 0) + last 3 years (delta = 1)
    "D": [1, 2, 3, 4, 5, 6, 7, 8]
    + [13, 14, 15, 20, 21, 22, 27, 28, 29]
    + [30, 31]
    + [56, 84]
    + [363, 364, 365, 727, 728, 729, 1091, 1092, 1093],
    # centered around each of the last 7 days (delta = 1) + last 4 weeks (delta = 1) + last 1 month (delta = 1) +
    #  last 8th and 12th weeks (delta = 0) + last 3 years (delta = 1)
    "2D": [1, 2, 3, 4, 5]
    + [6, 7, 8, 9, 10, 11, 13, 14, 15]
    + [16]
    + [28, 42]
    + [181, 182, 183, 363, 364, 365, 545, 546, 547],
    # centered around each of the last 3 months (delta = 0) + last 3 years (delta = 1) (assuming 52 weeks per year)
    "6D": [1, 2, 3, 4, 5, 6, 7, 9, 14]
    + [59, 60, 61, 120, 121, 122, 181, 182, 183],
    # centered around each of the last 3 months (delta = 0) + last 3 years (delta = 1) (assuming 52 weeks per year)
    "W": [1, 2, 3, 4, 5, 6, 7, 8, 12]
    + [51, 52, 53, 103, 104, 105, 155, 156, 157],
    # centered around each of the last 3 months (delta = 0) + last 3 years (delta = 1) (assuming 52 weeks per year)
    "8D": [1, 2, 3, 4, 5, 6, 7, 10] + [44, 45, 46, 90, 91, 92, 135, 136, 137],
    # centered around each of the last 3 years (delta = 1)
    "4W": [1, 2, 3, 4, 5, 6, 7, 12, 13, 14, 25, 26, 27, 38, 39, 40],
    # centered around each of the last 3 years (delta = 1)
    "3W": [1, 2, 3, 4, 5, 6, 7, 16, 17, 18, 33, 34, 35, 51, 52, 53],
    # centered around each of the last 3 years (delta = 1)
    "5W": [1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 19, 20, 21, 30, 31, 32],
    # centered around each of the last 3 years (delta = 1)
    M: [1, 2, 3, 4, 5, 6, 7, 11, 12, 13, 23, 24, 25, 35, 36, 37],
    # default
    "6" + M: [1, 2, 3, 4, 5, 6, 7],
    # default
    "12" + M: [1, 2, 3, 4, 5, 6, 7],
    Q: [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13],
    "QS": [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13],
    Y: [1, 2, 3, 4, 5, 6, 7],
    "YS": [1, 2, 3, 4, 5, 6, 7],
}

# For the default multiple (1)
for freq in ["min", H, "D", "W", M]:
    EXPECTED_LAGS["1" + freq] = EXPECTED_LAGS[freq]

# For frequencies that do not have unique form
EXPECTED_LAGS["60min"] = EXPECTED_LAGS["1" + H]
EXPECTED_LAGS["24" + H] = EXPECTED_LAGS["1D"]
EXPECTED_LAGS["7D"] = EXPECTED_LAGS["1W"]


@pytest.mark.parametrize("freq_str, expected_lags", EXPECTED_LAGS.items())
def test_lags(freq_str, expected_lags):
    lags = date_feature_set.get_lags_for_frequency(freq_str)
    assert lags == expected_lags


if __name__ == "__main__":
    test_lags()
