#!/usr/bin/env python3
# Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved


from typing import Callable, Type

from torch import nn


def _replace_child(
    root: nn.Module, child_name: str, converter: Callable[[nn.Module], nn.Module]
) -> None:
    """ A helper function, given the root module (e.g. x) and
    string representing the name of the submodule
    (e.g. y.z) converts the sub-module to a new module
    with the given converter.
    """
    # find the immediate parent
    parent = root
    nameList = child_name.split(".")
    for name in nameList[:-1]:
        parent = parent._modules[name]
    # set to identity
    parent._modules[nameList[-1]] = converter(parent._modules[nameList[-1]])


def replace_all_modules(
    root: nn.Module,
    target_class: Type[nn.Module],
    converter: Callable[[nn.Module], nn.Module],
) -> nn.Module:
    """
    Given a module `root`, and a `target_class` of type nn.Module,
    all the submodules (of root) that have the same
    type as target_class will be converted given the converter.

    Args:
        root: The model or a module instance with potentially sub-modules
        target_class: The target class of type nn.module that needs
                      to be replaced.
        converter: Is a function or a lambda that converts an instance
                   of a given target_class to another nn.Module.

    Returns:
        The module with all the `target_class` types replaced using
        the `converter`. `root` is modified and is equal to the return value."""
    # base case
    if isinstance(root, target_class):
        return converter(root)

    for name, obj in root.named_modules():
        if isinstance(obj, target_class):
            _replace_child(root, name, converter)
    return root


def batchnorm_to_instancenorm(module: nn.modules.batchnorm._BatchNorm) -> nn.Module:
    """
    Converts a BatchNorm `module` to the corresponding InstanceNorm module
    """

    def matchDim():
        if isinstance(module, nn.BatchNorm1d):
            return nn.InstanceNorm1d
        elif isinstance(module, nn.BatchNorm2d):
            return nn.InstanceNorm2d
        elif isinstance(module, nn.BatchNorm3d):
            return nn.InstanceNorm3d

    return matchDim()(module.num_features)


def batchnorm_to_groupnorm(module: nn.modules.batchnorm._BatchNorm) -> nn.Module:
    """
    Converts a BatchNorm `module` to GroupNorm module.

    Note:
        A default value of 32 is chosen for the number of groups based on the
        paper *Accurate, Large Minibatch SGD: Training ImageNet in 1 Hour*
        https://arxiv.org/pdf/1706.02677.pdf
    """
    return nn.GroupNorm(min(32, module.num_features), module.num_features, affine=False)


def nullify_batchnorm_modules(root: nn.Module, target_class):
    """
    Replaces all the submodules of type nn.BatchNormXd in `root` with
    nn.Identity.
    """
    return replace_all_modules(
        root, nn.modules.batchnorm._BatchNorm, lambda _: nn.Identity()
    )


def replace_batchnorm(model: nn.Module):
    return replace_all_modules(
        model, nn.modules.batchnorm._BatchNorm, batchnorm_to_groupnorm)
