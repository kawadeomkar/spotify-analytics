from functools import reduce, wraps
from quart import Blueprint, redirect, session, render_template
from typing import Dict, List, Tuple, Union

import auth
import operator
import pandas as pd
import redis_cache
import spotify
import time
import ujson
import util

log = util.setLogger(__name__)
graphs_route = Blueprint('graphs_route', __name__)


@graphs_route.route('/graphs')
async def graphs():
    validate = auth.validateAccessToken()
    if validate:
        return await redirect(validate)

    access_token = session['access_token']
    try:
        user_gtom = redis_cache.get_user_genre_track_obj_map(access_token)
        df_gtom = _convert_json_to_pandas_df(user_gtom)
        maa_df = _monthly_added_at_graph(df_gtom)
        maa_df = [{"date": added_at, "count": count} for added_at, count in maa_df.items()]

    except Exception as e:
        raise Exception(str(e))

    return await render_template('graphs.html', maa_df=maa_df)


def df_to_pds(func):
    """Calculates pd.DataFrame -> python data structure conversion runtime and returns result"""

    @wraps(func)
    def convert(*args, **kwargs):
        start = time.perf_counter()
        pds = func(*args, **kwargs).to_dict()  # to_dict('records')
        # pds = func(*args, **kwargs).values.tolist()
        end = time.perf_counter()
        runt = end - start
        print(f"Converted {func.__name__!r} in {runt:.4f} seconds")
        return pds

    return convert


@df_to_pds
def _monthly_added_at_graph(df_gtom: pd.DataFrame) -> pd.DataFrame:
    # Assumes index is a datetime object
    maa_df = df_gtom['genre'].groupby([pd.Grouper(freq='M')]).size()
    maa_df = _month_year_added_at_format_time(maa_df)
    return maa_df


def _monthly_stacked_genre_barchart(df_gtom: pd.DataFrame) -> pd.DataFrame:
    msbc_df = df_gtom[['genre']].groupby([pd.Grouper(freq='M'), 'genre'], as_index=False).size()
    msbc_df = _month_year_added_at_format_time(msbc_df)
    msbc_dict = {}
    for _, row in msbc_df.iterrows():
        if row['added_at'] not in msbc_dict:
            msbc_dict[row['added_at']] = {}
        msbc_dict[row['added_at']][row['genre']] = row['size']
    return msbc_dict


# Currently only applies function to index
def _month_year_added_at_format_time(df_gtom: pd.DataFrame) -> pd.DataFrame:
    if df_gtom.index.name == 'added_at':
        df_gtom.index = df_gtom.index.map(lambda x: f"{x.month}-{x.year}")
    elif 'added_at' in df_gtom:
        df_gtom['added_at'] = df_gtom['added_at'].apply(lambda x: f"{x.month}-{x.year}")
    else:
        raise Exception('Cannot format time column')
    return df_gtom


def _popularity_mean(df_gtom: pd.DataFrame) -> float:
    return df_gtom['popularity'].mean()


def _convert_json_to_pandas_df(user_gtom):
    # normalize gtom dict to list of dicts
    for genre, t_objs in user_gtom.items():
        for t_obj in t_objs:
            t_obj['genre'] = genre
    to_df = reduce(operator.iconcat, user_gtom.values(), [])
    df_gtom = pd.json_normalize(to_df)
    df_gtom['added_at'] = pd.to_datetime(df_gtom['added_at'])
    df_gtom = df_gtom.set_index('added_at')

    # docker cp quart_sp:/usr/src/data.csv .
    # df_gtom.to_csv('data.csv', encoding='utf-8')

    return df_gtom
