import collections
from copy import deepcopy
from functools import reduce, wraps
from typing import List

from quart import Blueprint, redirect, session, render_template

import auth
import heapq
import operator
import pandas as pd
import redis_cache
import time
import ujson
import util

log = util.setLogger(__name__)
graphs_route = Blueprint('graphs_route', __name__)


@graphs_route.route('/graphs')
async def graphs():
    validate = auth.validateAccessToken()
    if validate:
        return redirect(validate)

    access_token = session['access_token']
    try:
        user_gtom = redis_cache.get_user_genre_track_obj_map(access_token)
        df_gtom = _convert_json_to_pandas_df(user_gtom)
        maa_df = df_gtom.copy(deep=True)
        maa_df = _monthly_added_at_graph(maa_df)
        maa_df = [{"date": added_at, "count": count} for added_at, count in maa_df.items()]

        log.info(f"MGC DF BEFORE COPY: {df_gtom}")
        mgc_df = df_gtom.copy(deep=True)
        mgc_dict, mgc_genres, mgc_height = _monthly_genre_count_graph(mgc_df)


    except Exception as e:
        raise Exception(str(e))

    return await render_template('graphs.html', maa_df=maa_df, mgc_dict=mgc_dict,
                                 mgc_genres=mgc_genres, mgc_height=mgc_height)


def df_to_pds(func):
    """For testing
    Calculates pd.DataFrame -> python data structure conversion runtime and returns result"""

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


def _monthly_added_at_graph(df_gtom: pd.DataFrame) -> pd.DataFrame:
    # Assumes index is a datetime object
    maa_df = df_gtom.drop_duplicates(subset='track_id', keep='last')
    log.info(maa_df.head())
    maa_df = maa_df.groupby(
        [pd.Grouper(freq='M')]).size()
    log.info(maa_df.head())
    maa_df = _month_year_added_at_format_time(maa_df)
    return maa_df


def _monthly_genres(mgc_row):
    """mgc_row: dictionary of one month of {genre->size} with an added_at key,
    contains all genres (unstacked from transpose on multiindex from groupby)"""
    mgc_genre_set = deepcopy(mgc_row)
    del mgc_genre_set['added_at']
    mgc_genre_set = mgc_genre_set.keys()
    if 'NA' in mgc_genre_set:
        del mgc_genre_set['NA']
    return mgc_genre_set


def _monthly_genre_count_graph(df_gtom: pd.DataFrame):
    log.info(df_gtom.index)
    log.info(f"DF GTOM MGC {df_gtom.head()}, DTYPES: {df_gtom.dtypes}")
    mgc_df = df_gtom[['genre']].groupby([pd.Grouper(freq='M'), 'genre']).size() \
        .unstack(level=1).reset_index().drop('NA', axis=1, errors='ignore').fillna(0)
    mgc = _month_year_added_at_format_time(mgc_df).to_dict('records')

    # genre_set = _monthly_genres(mgc[0]) # too many genres in d3 group bar

    log.info(f"MGC MAP: {mgc}")
    # top 10 genres per month and collective genres
    mgc, mgc_genre_set, max_height = _monthly_stacked_genre_bc_filter(list(mgc))
    return mgc, mgc_genre_set, max_height


def _monthly_stacked_genre_barchart(df_gtom: pd.DataFrame) -> pd.DataFrame:
    msbc_df = df_gtom[['genre']].groupby([pd.Grouper(freq='M'), 'genre'], as_index=False).size()
    msbc_df = _month_year_added_at_format_time(msbc_df)
    msbc_dict = {}

    for _, row in msbc_df.iterrows():
        if row['added_at'] not in msbc_dict:
            msbc_dict[row['added_at']] = {}
        msbc_dict[row['added_at']][row['genre']] = row['size']
    return msbc_dict


def _monthly_stacked_genre_bc_filter(mgc_list: List[dict]):
    """IN PLACE"""

    mgc_genres = set()
    max_height = 0
    for i in range(len(mgc_list)):
        add_val = mgc_list[i]['added_at']
        del mgc_list[i]['added_at']
        top_ten = dict(collections.Counter(mgc_list[i]).most_common(10))
        mgc_genres.update(list(top_ten.keys()))
        max_height = max(max_height, sum(top_ten.values()))
        top_ten['added_at'] = add_val
        mgc_list[i] = top_ten

    log.info(f"MGBC FILTER MGC LIST {mgc_list}")
    log.info(f"MGBC FILTER MGC GENRES {mgc_genres}")
    return mgc_list, list(mgc_genres), max_height


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
    # log.info(f"GENRE KEYS: {user_gtom.keys()} LEN {len(user_gtom)}")
    for obj in user_gtom:
        if 'name' not in obj.keys() or 'album' not in obj.keys() or 'artists' \
                not in obj.keys() or 'popularity' not in obj.keys() \
                or 'genre' not in obj.keys() \
                or 'added_at' not in obj.keys() or 'track_id' \
                not in obj.keys():
            raise Exception(f"TRACK OBJ MISSING KEYS {str(obj)}")
        log.info(f"TO DF FIRST 5 {user_gtom[:4]}")
    to_df = user_gtom  # reduce(operator.iconcat, user_gtom.values(), [])
    log.info(f"TO DF: {to_df[0]}")

    df_gtom = pd.DataFrame(to_df, index=None)
    df_gtom = df_gtom.loc[:, ~df_gtom.columns.str.contains('^Unnamed')]
    log.info(f"DF DTYPES BEFORE {df_gtom.dtypes}")
    log.info(f"DF HEAD {df_gtom.iloc[:4]}")
    log.info(df_gtom['added_at'])
    df_gtom['added_at'] = pd.to_datetime(df_gtom['added_at'])

    log.info(f"DF DTYPES: {df_gtom.dtypes}")
    df_gtom = df_gtom.set_index('added_at')

    log.info(f" DF TYPE {type(df_gtom)}")
    # log.info(f"{df_gtom.head}")
    # docker cp quart_sp:/usr/src/quart_sp/data.csv .
    df_gtom.to_csv('data.csv', encoding='utf-8')

    return df_gtom
