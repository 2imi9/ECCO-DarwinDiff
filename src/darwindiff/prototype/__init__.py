"""Micro prototype for ECCO-DarwinDiff.

A 1D toy reaction-diffusion simulator + small parameter MLP used to validate that the
differentiable scaffold works end-to-end (PyTorch autograd through hand-coded physics,
MLP-predicts-parameter composition, gradient descent recovery of known synthetic
parameters) before committing to the specific Darwin biogeochemistry equations.

The toy is method-agnostic — same scaffold later swaps in real Darwin equations and real
parameters once the equation subset is locked with the domain advisor.
"""
