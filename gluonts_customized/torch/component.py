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
import torch

from gluonts_customized.core.component import equals, tensor_to_numpy


@equals.register(torch.Tensor)
def equals_tensor(this: torch.Tensor, that: torch.Tensor) -> bool:
    return torch.allclose(this, that)


@tensor_to_numpy.register(torch.Tensor)
def _(tensor: torch.Tensor) -> np.ndarray:
    return tensor.cpu().numpy()
