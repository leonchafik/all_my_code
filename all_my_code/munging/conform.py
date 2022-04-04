from pkg_resources import DistributionNotFound, get_distribution
import xarray as xr
from functools import wraps as _wraps

try:
    __version__ = get_distribution("all_my_code").version
except DistributionNotFound:
    __version__ = ""
del get_distribution, DistributionNotFound


def apply_process_pipeline(ds, *funcs):
    """
    Applies a list of functions to an xarray.Dataset object.
    Functions must accept a Dataset and return a Dataset
    """
    for func in funcs:
        ds = func(ds)
    return ds


class add_docs_line1_to_attribute_history(object):
    def __init__(self, func):
        self.func = func
        self.name = func.__name__
        docs = func.__doc__
        self.msg = docs.strip().split("\n")[0] if isinstance(docs, str) else ""

    def __call__(self, *args, **kwargs):
        if len(args) == 1:
            try:
                out = self._add_history(self.func(*args, **kwargs))
                return out
            except Exception as e:
                raise e
                return args[0]

        self.kwargs = kwargs
        return self.__caller__

    def __caller__(self, ds):
        return self._add_history(self.func(ds, **self.kwargs))

    def _add_history(self, ds, key='history'):
        from pandas import Timestamp

        version = ".{__version__}" if __version__ else ""
        
        now = Timestamp.today().strftime("%y%m%d")
        prefix = f"[amc{version}@{now}] "
        msg = prefix + self.msg
        
        hist = ds.attrs.get(key, '')
        if hist != '':
            hist = hist.split(";")
            hist = [h.strip() for h in hist]
            msg = "; ".join(hist + [msg])
            
        ds = ds.assign_attrs({key: msg})

        return ds


@add_docs_line1_to_attribute_history
def lon_180W_180E(ds, lon_name='lon'):
    """
    Regrid the data to [-180 : 180] from [0 : 360]
    """
    names = set(list(ds.coords) + list(ds.dims))
    if lon_name not in names:
        return ds
    
    lon180 = (ds[lon_name] - 180) % 360 - 180
    return ds.assign_coords(**{lon_name: lon180}).sortby(lon_name)


@add_docs_line1_to_attribute_history
def lon_0E_360E(ds, lon_name='lon'):
    """
    Regrid the data to [0 : 360] from [-180 : 180] 
    """
    names = set(list(ds.coords) + list(ds.dims))
    if lon_name not in names:
        return ds
    
    lon360 = ds[lon_name].values % 360
    ds = ds.assign_coords(**{lon_name: lon360}).sortby(lon_name)
    return ds
    
    
@add_docs_line1_to_attribute_history  
def coord_05_offset(ds, center=0.5, coord_name='lon'):
    """
    Interpolate data if the grid centers are offset.
    Only works for 1deg data
    
    Parameters
    ----------
    ds: xr.Dataset
        the dataset with a coordinate variable variable
    center: float
        the desired center point of the grid points between 0 - 1
    coord_name: str [lon]
        the name of the coordinate 
        
    Returns
    -------
    xr.Dataset: interpolated onto the new grid with the new
        coord being the old coord + center
    """

    def has_coords(ds, checklist=['time', 'lat', 'lon']):
        """
        Check that data has coordinates
        """
        matches = {key: (key in ds.coords) for key in checklist}
        if all(matches.values()):
            return 1
        else:
            return 0

    center = center - (center // 1)
    if has_coords(ds):
        coord = ds[coord_name].values
        mod = coord - (coord // 1)
        # use the modulus to determine if grid centers are correct
        if any(mod != center):
            ds = ds.interp({coord_name: coord + center})
            
    return ds
    
    
@add_docs_line1_to_attribute_history
def transpose_dims(ds, default=['time', 'depth', 'lat', 'lon'], other_dims_before=True):
    """
    Transpose dimensions to [time, depth, lat, lon]. 
    Can specify if remaining dimensions should be ordered before 
    or after the default dimensions.
    """
    old_order = list(ds.dims)
    dims = set(old_order)
    default = [d for d in default if d in dims]
    default_set = set(default)
    other = dims - default_set
    
    if other_dims_before:
        new_order = list(other) + list(default)
    else:
        new_order = list(default) + list(other)
    
    matching = all([a==b for a,b in zip(ds.dims, new_order)])
    if not matching:
        ds = ds.transpose(*new_order)
    
    return ds


@add_docs_line1_to_attribute_history
def correct_coord_names(
    ds, 
    match_dict=dict(
        time=["month", "time", "t"],
        depth=["depth", "z", "lev", "z_t", "z_l"],
        lat=["lat", "latitude", "y"], 
        lon=["lon", "longitude", "x"])
):
    """
    Rename coordinates to [time, lat, lon, depth] with fuzzy matching
    
    Parameters
    ----------
    ds: xr.Dataset
    match_dict: dict
        A dictionary where the keys are the desired coordinate/dimension names
        The values are the nearest guesses for possible names. Note these do 
        not have to match the possible names perfectly. 
        
    Returns
    -------
    xr.Dataset: with renamed coordinates that match the keys from match_dict
    """
    from . name_matching import guess_coords_from_column_names
    
    coord_keys = list(set(list(ds.coords) + list(ds.dims)))
    coord_renames = guess_coords_from_column_names(coord_keys, match_dict=match_dict)
    
    if any(coord_renames):
        ds = ds.rename(coord_renames)
    
    return ds


@add_docs_line1_to_attribute_history
def interpolate_1deg(xds, method="linear"):
    """
    interpolate the data to 1 degree resolution [-89.5 : 89.5] x [-179.5 : 179.5]
    """
    from warnings import warn
    from numpy import arange

    if xds.lon.max() > 180:
        warn("Longitude range is from 0 to 360, interpolate_1deg only works for -180 to 180")

    attrs = xds.attrs
    xds = (
        xds.interp(lat=arange(-89.5, 90), lon=arange(-179.5, 180), method=method)
        # filling gaps due to interpolation along 180deg
        .roll(lon=180, roll_coords=False)
        .interpolate_na(dim="lon", limit=3)
        .roll(lon=-180, roll_coords=False)
    )

    xds.attrs = attrs

    return xds


@add_docs_line1_to_attribute_history
def time_center_monthly(ds, center_day=15, time_name='time'):
    """
    Date centered on a given date (default 15th)
    
    Data must be monthly for this function to work
    """
    from pandas import Timedelta as timedelta
    from . date_utils import datetime64ns_to_lower_order_datetime
    
    time = datetime64ns_to_lower_order_datetime(ds[time_name].values)
    
    if "[M]" not in str(time.dtype):
        raise ValueError("data time variable is not monthly")
    
    delta_days = timedelta(f'{center_day - 1}D')
    
    ds = ds.assign_coords(time=time.astype('datetime64[D]') + delta_days)
    
    return ds


_func_registry = [
    lon_0E_360E,
    lon_180W_180E,
    interpolate_1deg,
    coord_05_offset,
    transpose_dims,
    correct_coord_names,
    time_center_monthly,
]

@xr.register_dataset_accessor("conform")
@xr.register_dataarray_accessor("conform")
class DataConform(object):
    def __init__(self, xarray_obj):
        self._obj = xarray_obj

        for wrapped in _func_registry:
            setattr(self, wrapped.func.__name__, self._make_accessor_func(wrapped))

    def _make_accessor_func(self, wrapped):
        @_wraps(wrapped.func)
        def run_func(*args, **kwargs):
            return wrapped(self._obj, *args, **kwargs)

        return run_func
