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

from typing import List

from mxnet.gluon import nn

from gluonts_customized.core.component import validated
from gluonts_customized.mx import Tensor


class MLP(nn.HybridBlock):
    """
    Defines an MLP block.

    Parameters
    ----------
    layer_sizes
        number of hidden units per layer.

    flatten
        toggle whether to flatten the output tensor.

    activation
        activation function of the MLP, default is relu.
    """

    @validated()
    def __init__(
        self, layer_sizes: List[int], flatten: bool, activation="relu"
    ) -> None:
        super().__init__()
        self.layer_sizes = layer_sizes
        with self.name_scope():
            self.layers = nn.HybridSequential()
            for layer, layer_dim in enumerate(layer_sizes):
                self.layers.add(
                    nn.Dense(layer_dim, flatten=flatten, activation=activation)
                )

    def hybrid_forward(self, F, x: Tensor) -> Tensor:
        """
        Parameters
        ----------
        F
            A module that can either refer to the Symbol API or the NDArray
            API in MXNet.
        x
            Input tensor

        Returns
        -------
        Tensor
            Output of the MLP given the input tensor.
        """
        return self.layers(x)
