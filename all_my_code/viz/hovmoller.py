def make_zonal_anomaly_plot_data(da):
    da_zon_mean = da.mean('lon').dropna('lat', how='all')
    lat_avg = da_zon_mean.mean('time')
    da_zon_anom = da_zon_mean - lat_avg
    da_zon_anom_an = da_zon_anom.resample(time='1AS').mean().T
    
    return lat_avg, da_zon_anom_an


def plot_zonal_anom(da, ax=None, lw=0.5, **kwargs): 
    from matplotlib import pyplot as plt
    
    if ax is not None:
        assert len(ax) == 2, 'ax must have two axes objects'
        fig = ax[0].get_figure()

    if ax is None:
        fig = plt.gcf()
        
        ax = [
            plt.subplot2grid([1, 5], [0, 0], colspan=1),
            plt.subplot2grid([1, 5], [0, 1], colspan=4),
        ]

    name = da.attrs.get('long_name', getattr(da, 'name', ''))
    unit = da.attrs.get('units', '')
    
    lat_avg, zon_anom = make_zonal_anomaly_plot_data(da)
    
    x1 = lat_avg.values
    y1 = lat_avg.lat.values
    
    ax[0].plot(x1, y1, color='k', lw=1.5)

    props = dict(
        cbar_kwargs=dict(pad=0.03, aspect=16, label=f'{name} [{unit}]'),
        robust=True, 
        levels=11, 
        ax=ax[1])
    props.update(kwargs)

    if props.get('add_colorbar') is False:
        props.pop('cbar_kwargs')

    img = zon_anom.plot.contourf(**props)
    if lw > 0:
        cnt = zon_anom.plot.contour(
            ax=ax[1],
            linewidths=[lw], 
            levels=img.levels, 
            alpha=0.4,
            colors=['k'])
    
    ax[0].set_ylabel('Latitude (°N)')
    ax[0].set_yticks([])
    ax[0].set_yticklabels([])
    
    plt.sca(ax[1])
    plt.xticks(rotation=0, ha='center')
    ax[1].set_yticks([])
    ax[1].set_ylabel('')
    ax[1].set_xlabel('')
    ax[1].set_yticks([-60, -30, 0, 30, 60])
    ax[1].set_yticklabels(['60°S', '30°S', 'EQ', '30°N', '60°N'])

    [a.set_visible(True) for a in ax[1].spines.values()]
    [ax[0].spines[side].set_visible(False) for side in ['top', 'right', 'left']]

    ax[0].set_ylim(ax[1].get_ylim())

    fig.tight_layout()
    fig.subplots_adjust(right=0.9, hspace=0.1)
    
    return ax[0], img


def plot_zonal_anom_with_trends(da, ax=None, lw=0.5, **kwargs):
    from matplotlib import pyplot as plt
    
    if ax is None:
        fig = plt.gcf()
        ax = [
            plt.subplot2grid([1, 6], [0, 0], colspan=1),
            plt.subplot2grid([1, 6], [0, 1], colspan=4),
            plt.subplot2grid([1, 6], [0, 5], colspan=1)]
    assert len(ax) == 3, 'ax must be three axes'
    
    lat_avg, hovmol_data = make_zonal_anomaly_plot_data(da)
    lat_trend = hovmol_data.ts.slope(dim='time').smooth.ewm(dim='lat', radius=2)

    # the zonal anomaly function takes the first two axes objects as input
    # and we create the third plot manually form the lat_trend data
    props = dict(levels=21, add_colorbar=False, extend='both')
    props.update(kwargs)
    img = da.viz.zonal_anomally(ax=ax[:2], lw=lw, **props)[1]

    yticks = ax[1].get_yticks()
    ylabels = [l.get_text() for l in ax[1].get_yticklabels()]

    ax[1].set_yticklabels([])
    ax[1].set_yticks([])

    ax[0].set_yticks(yticks)
    ax[0].set_yticklabels(ylabels)

    ax[2].plot(lat_trend.values, lat_trend.lat, color='k', lw=ax[0].get_lines()[0].get_lw())
    ax[2].yaxis.set_label_position("right")
    ax[2].yaxis.tick_right()
    ax[2].set_yticks(yticks)
    ax[2].set_yticklabels(ylabels)
    ax[2].set_ylabel(ax[0].get_ylabel())

    ax[2].spines['left'].set_visible(False)
    ax[2].spines['right'].set_visible(True)
    ax[0].spines['left'].set_visible(True)

    fig.tight_layout()
    
    ax[1].colorbar = plt.colorbar(img, ax=[ax], location='top', shrink=.64, aspect=25)
    ax[1] = img
    
    return fig, ax