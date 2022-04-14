from . import conform
from . import date_utils
from . import colocation
from . import units
from . import sparse
from functools import wraps as _wraps
from ..utils import (
    make_xarray_accessor as _make_xarray_accessor, 
    get_unwrapped, 
    add_docs_line1_to_attribute_history)

from xarray import (
    register_dataset_accessor as _register_dataset, 
    register_dataarray_accessor as _register_dataarray)


from .colocation import colocate_dataarray as _colocate_dataarray
from .grid import (
    lon_180W_180E as _lon_180W_180E, 
    lon_0E_360E as _lon_0E_360E, 
    coord_05_offset as _coord_05_offset, 
    coarsen as _coarsen,
    regrid as _regrid,
    resample as _resample,
    interp as _interp)
from .conform import (
    transpose_dims as _transpose_dims,
    correct_coord_names as _correct_coord_names,
    time_center_monthly as _time_center_monthly,
    drop_0d_coords as _drop_0d_coords,
    rename_vars_snake_case as _rename_vars_snake_case,
    apply_process_pipeline as _apply_process_pipeline,
)
    

_make_xarray_accessor(
    "grid",
    [
        _lon_180W_180E,
        _lon_0E_360E,
        _coord_05_offset,
        _colocate_dataarray,
        _interp,
        _regrid,
        _coarsen,
        _resample,
    ],
    accessor_type='both',
    add_docs_line_to_history=False,
)


_func_registry = [
    _lon_0E_360E,
    _lon_180W_180E,
    _coord_05_offset,
    _transpose_dims,
    _correct_coord_names,
    _rename_vars_snake_case,
    _time_center_monthly,
    _drop_0d_coords,
]


@_register_dataset("conform")
@_register_dataarray("conform")
class DataConform(object):
    """
    A class to conform a dataset/dataarray to a the desired conventions

    Modules (subfunctions) can be used to conform the dataset/dataarray 
    individually, or you can call this function to apply a set of standard 
    functions. 
    """
    def __init__(self, xarray_obj):
        self._obj = xarray_obj

        for func in _func_registry:
            func = add_docs_line1_to_attribute_history(func)
            setattr(self, get_unwrapped(func).__name__, self._make_accessor_func(func))

    def _make_accessor_func(self, func):
        @_wraps(get_unwrapped(func))
        def run_func(*args, **kwargs):
            return func(self._obj, *args, **kwargs)

        return run_func

    def __call__(
        self, 
        correct_coord_names=True,
        time_center_monthly=False,
        drop_0d_coords=True,
        transpose_dims=True,
        lon_180W_180E=True,
        rename_vars_snake_case=False,
    ):
        da = self._obj

        funclist = []
        if correct_coord_names:
            funclist.append(_correct_coord_names)
        if time_center_monthly:
            funclist.append(_time_center_monthly)
        if drop_0d_coords:
            funclist.append(_drop_0d_coords)
        if transpose_dims:
            funclist.append(_transpose_dims)
        if lon_180W_180E:
            funclist.append(_lon_180W_180E)
        if rename_vars_snake_case:
            funclist.append(_rename_vars_snake_case)

        funclist = [add_docs_line1_to_attribute_history(f) for f in funclist]
        out = _apply_process_pipeline(da, *funclist)

        return out

