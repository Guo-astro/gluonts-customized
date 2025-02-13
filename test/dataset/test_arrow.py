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

import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

from gluonts_customized.dataset.arrow import (
    File,
    ArrowWriter,
    ParquetWriter,
)


def assert_equal(left, right):
    for lval, rval in zip(left, right):
        np.testing.assert_equal(lval, rval)


def rand_start():
    year = np.random.randint(low=1900, high=2020)
    month = np.random.randint(low=1, high=13)
    day = np.random.randint(low=1, high=29)
    return f"{year}-{month:02d}-{day:02d}"


def make_data(n: int):
    data = []
    for i in range(n):
        ts_len = np.random.choice([1, 100, 700, 901])
        ts = {
            "start": rand_start(),
            "target": np.random.uniform(size=ts_len).astype(np.float32),
            "feat_dynamic_real": np.random.uniform(size=(3, ts_len)).astype(
                np.float32
            ),
            "feat_static_cat": np.random.randint(
                low=0, high=10, size=7
            ).astype(np.int64),
        }
        data.append(ts)
    return data


@pytest.mark.skipif(sys.version_info < (3, 7), reason="Requires PyArrow v8.")
@pytest.mark.parametrize(
    "writer",
    [
        ArrowWriter(stream=True, metadata={"freq": "H"}, compression="lz4"),
        ArrowWriter(stream=False, metadata={"freq": "H"}),
        ParquetWriter(metadata={"freq": "H"}),
    ],
)
@pytest.mark.parametrize("flatten_arrays", [True, False])
def test_arrow(writer, flatten_arrays):
    data = make_data(10)
    writer.flatten_arrays = flatten_arrays

    with tempfile.TemporaryDirectory() as path:
        path = Path(path, "data.arrow")

        # create file on disk
        writer.write_to_file(data, path)

        dataset = File.infer(path)

        assert len(data) == len(dataset)
        assert dataset.metadata()["freq"] == "H"

        assert_equal(data, dataset)

        assert_equal(dataset[4], data[4])

        assert len(dataset[:5]) == len(data[:5])
        assert_equal(dataset[:5], data[:5])

        assert len(dataset[10:]) == len(data[10:])
        assert_equal(dataset[10:], data[10:])

        assert len(dataset[3:7]) == len(data[3:7])
        assert_equal(dataset[3:7], data[3:7])

        assert len(dataset[3:7][1:-1]) == len(data[3:7][1:-1])
        assert_equal(dataset[3:7][1:-1], data[3:7][1:-1])
