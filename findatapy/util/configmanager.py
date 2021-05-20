__author__ = 'saeedamen' # Saeed Amen

#
# Copyright 2016 Cuemacro
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
# License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#
# See the License for the specific language governing permissions and limitations under the License.
#

import os

import csv
import pandas as pd

from findatapy.util.dataconstants import DataConstants
from findatapy.util.singleton import Singleton
from findatapy.util.loggermanager import LoggerManager
from dateutil.parser import parse

import re

import threading

class ConfigManager(object):
    """Functions for converting between vendor tickers and findatapy tickers (and vice-versa).

    """
    __metaclass__ = Singleton

    # Tickers and fields
    _dict_time_series_tickers_list_library_to_vendor = {}
    _dict_time_series_tickers_list_vendor_to_library = {}
    _dict_time_series_fields_list_vendor_to_library = {}
    _dict_time_series_fields_list_library_to_vendor = {}

    # Store expiry date
    _dict_time_series_ticker_expiry_date_library_to_library = {}

    # Store categories -> fields
    _dict_time_series_category_fields_library_to_library = {}
    _dict_time_series_category_startdate_library_to_library = {}
    _dict_time_series_category_tickers_library_to_library = {}

    # category, source, freq, ticker, cut, fields, sourceticker, local-close, expiry, ldn_clo
    _data_frame_time_series_tickers = None

    # Store categories ->
    _dict_time_series_tickers_list_library = {}

    __lock = threading.Lock()

    __instance = None

    def __init__(self, *args, **kwargs):
        pass

    def get_instance(cls, data_constants=None):
        if not ConfigManager.__instance:
            with ConfigManager.__lock:
                if not ConfigManager.__instance:
                    ConfigManager.__instance = super(ConfigManager, cls).__new__(ConfigManager)

                    if data_constants is None:
                        data_constants = DataConstants()

                    ConfigManager.__instance.populate_time_series_dictionaries(data_constants=data_constants)

        return ConfigManager.__instance


    ### time series ticker manipulators
    @staticmethod
    def populate_time_series_dictionaries(data_constants=None):

        if data_constants is None:
            data_constants = DataConstants()

        # There are several CSV files which contain data on the tickers

        # time_series_tickers_list - contains every tickers (findatapy tickers => vendor tickers)
        # category,	data_source,	freq, tickers, cut, fields, vendor_tickers (from your data provider)
        # eg. fx / bloomberg / daily / EURUSD / TOK / close,open,high,low / EURUSD CMPT Curncy

        # time_series_fields_list - translate findatapy fields name to vendor fields names
        # findatapy fields => vendor fields
        # data_source, fields, vendor_fields

        # time_series_categories_fields - for each category specific generic properties
        # category,	freq, data_source, fields, startdate
        # eg. fx / daily / bloomberg / close,high,low,open / 01-Jan-70

        # eg. bloomberg / close / PX_LAST

        ## Populate tickers list (allow for multiple files)
        time_series_tickers_list_file = data_constants.time_series_tickers_list.split(';')

        df_tickers = []

        for tickers_list_file in time_series_tickers_list_file:

            if os.path.isfile(tickers_list_file):
                reader = csv.DictReader(open(tickers_list_file))
                df_tickers.append(pd.read_csv(tickers_list_file))

                for line in reader:
                    category = line["category"]
                    data_source = line["data_source"]
                    freq_list = line["freq"].split(',')

                    if isinstance(freq_list, str):
                        freq_list = [freq_list]

                    for freq in freq_list:
                        tickers = line["tickers"]
                        cut = line["cut"]
                        vendor_tickers = line["vendor_tickers"]
                        expiry = None

                        try:
                            expiry = line['expiry']
                        except:
                            pass

                        if category != "":
                            # print("stop" + category + '.' +
                            #                                                  data_source + '.' +
                            #                                                  freq + '.' +
                            #                                                  cut + '.' +
                            #                                                  tickers)

                            # Conversion from library tickers to vendor vendor_tickers
                            ConfigManager._dict_time_series_tickers_list_library_to_vendor[category + '.' +
                                                                                 data_source + '.' +
                                                                                 freq + '.' +
                                                                                 cut + '.' +
                                                                                 tickers] = vendor_tickers

                            try:
                                if expiry != '':
                                    expiry = parse(expiry)
                                else:
                                    expiry = None
                            except:
                                pass

                            # Conversion from library tickers to library expiry date
                            ConfigManager._dict_time_series_ticker_expiry_date_library_to_library[
                                                                                           data_source + '.' +
                                                                                           tickers] = expiry

                            # Conversion from vendor vendor_tickers to library tickers
                            ConfigManager._dict_time_series_tickers_list_vendor_to_library[data_source + '.' + vendor_tickers] = tickers

                            # Library of tickers by category
                            key = category + '.' + data_source + '.' + freq + '.' + cut

                            if key in ConfigManager._dict_time_series_category_tickers_library_to_library:
                                ConfigManager._dict_time_series_category_tickers_library_to_library[key].append(tickers)
                            else:
                                ConfigManager._dict_time_series_category_tickers_library_to_library[key] = [tickers]

        ConfigManager._data_frame_time_series_tickers = pd.concat(df_tickers)

        ## Populate fields conversions
        reader = csv.DictReader(open(data_constants.time_series_fields_list))

        for line in reader:
            data_source = line["data_source"]
            fields = line["fields"]
            vendor_fields = line["vendor_fields"]

            # Conversion from vendor vendor_fields to library fields
            ConfigManager._dict_time_series_fields_list_vendor_to_library[data_source + '.' + vendor_fields] = fields

            # Conversion from library tickers to vendor vendor_fields
            ConfigManager._dict_time_series_fields_list_library_to_vendor[data_source + '.' + fields] = vendor_fields

        ## Populate categories fields list
        reader = csv.DictReader(open(data_constants.time_series_categories_fields))

        for line in reader:
            category = line["category"]
            data_source = line["data_source"]
            freq = line["freq"]
            cut = line["cut"]
            fields = line["fields"].split(',') # Can have multiple fields
            startdate = line["startdate"]

            if category != "":
                # Conversion from library category to library fields list
                ConfigManager._dict_time_series_category_fields_library_to_library[
                    category + '.' + data_source + '.' + freq + '.' + cut] = fields

                # Conversion from library category to library startdate
                ConfigManager._dict_time_series_category_startdate_library_to_library[
                        category + '.' + data_source + '.' + freq + '.' + cut] = parse(startdate).date()

    def free_form_tickers_regex_query(self, category=None, data_source=None, freq=None, cut=None, tickers=None, dict_filter={},
                                      ret_fields=['category', 'data_source', 'freq', 'cut'], smart_group=False):

        df = ConfigManager._data_frame_time_series_tickers

        if category is not None and not(df.empty):
            df = df[df['category'].str.match(category) == True]

        if data_source is not None and not(df.empty):
            df = df[df['data_source'].str.match(data_source) == True]

        if freq is not None and not(df.empty):
            df = df[df['freq'].str.match(freq) == True]

        if cut is not None and not(df.empty):
            df = df[df['cut'].str.match(cut) == True]

        if tickers is not None and not(df.empty):
            df = df[df['tickers'].str.match(tickers) == True]

        if cut is not None and not(df.empty):
            df = df[df['cut'].str.match(cut) == True]

        for k in dict_filter.keys():
            if k is not None and not(df.empty):
                df = df[df[k].str.match(dict_filter[k]) == True]

        if ret_fields is not None and not(df.empty):
            df = df[ret_fields]

        df = df.drop_duplicates()

        # Group any tickers/vendor_tickers together
        if smart_group:
            df = ConfigManager.smart_group_dataframe_tickers(df, ret_fields=ret_fields)

        return df

    @staticmethod
    def smart_group_dataframe_tickers(df, ret_fields=['category', 'data_source', 'freq', 'cut']):
        """Groups together a dataframe of metadata associated with assets
        """

        if set(['category', 'data_source', 'freq', 'cut']).issubset(ret_fields):
            group_fields = ret_fields.copy()

            agg_dict = {}

            if 'tickers' in ret_fields:
                df['tickers'] = [[x] for x in df['tickers'].tolist()]
                agg_dict['tickers'] = 'sum'
                group_fields.remove('tickers')

            if 'vendor_tickers' in ret_fields:
                df['vendor_tickers'] = [[x] for x in df['vendor_tickers'].tolist()]
                agg_dict['vendor_tickers'] = 'sum'
                group_fields.remove('vendor_tickers')

            if agg_dict != {}:
                df = df.groupby(group_fields).agg(agg_dict)

                for i, g in enumerate(group_fields):
                    df[g] = df.index.get_level_values(i)

                df = df.reset_index(drop=True)

        return df

    @staticmethod
    def get_dataframe_tickers():
        return ConfigManager._data_frame_time_series_tickers

    @staticmethod
    def get_categories_from_fields():
        return ConfigManager._dict_time_series_category_fields_library_to_library.keys()

    @staticmethod
    def get_categories_from_tickers():
        return ConfigManager._dict_time_series_category_tickers_library_to_library.keys()

    @staticmethod
    def get_categories_from_tickers_selective_filter(filter):
        initial_list = ConfigManager._dict_time_series_category_tickers_library_to_library.keys()
        filtered_list = []

        for category_desc in initial_list:
            split_cat = category_desc.split('.')

            category = split_cat[0]
            # data_source = split_cat[1]
            # freq = split_cat[2]
            # cut = split_cat[3]

            if filter in category:
                filtered_list.append(category_desc)

        return filtered_list

    @staticmethod
    def get_potential_caches_from_tickers():
        all_categories = ConfigManager._dict_time_series_category_tickers_library_to_library.keys()

        expanded_category_list = []

        for sing in all_categories:
            split_sing = sing.split(".")
            category = split_sing[0]
            data_source = split_sing[1]
            freq = split_sing[2]
            cut = split_sing[3]

            if(freq == 'intraday'):
                intraday_tickers = ConfigManager.get_tickers_list_for_category(category, data_source, freq, cut)

                for intraday in intraday_tickers:
                    expanded_category_list.append(category + '.' + data_source + '.' + freq +
                                                  '.' + cut + '.' + intraday)
            else:
                expanded_category_list.append(category + '.' + data_source + '.' + freq +
                                                  '.' + cut)

        return expanded_category_list

    @staticmethod
    def get_fields_list_for_category(category, data_source, freq, cut):
        return ConfigManager._dict_time_series_category_fields_library_to_library[
                category + '.' + data_source + '.' + freq + '.' + cut]

    @staticmethod
    def get_fields_list_for_category_str(category):
        return ConfigManager._dict_time_series_category_fields_library_to_library[category]

    @staticmethod
    def get_startdate_for_category(category, source, freq, cut):
        return ConfigManager._dict_time_series_category_startdate_library_to_library[
                category + '.' + source + '.' + freq + '.' + cut]

    @staticmethod
    def get_expiry_for_ticker(data_source, ticker):
        return ConfigManager._dict_time_series_ticker_expiry_date_library_to_library[
                data_source + '.' + ticker]

    @staticmethod
    def get_filtered_tickers_list_for_category(category, data_source, freq, cut, filter):
        tickers = ConfigManager._dict_time_series_category_tickers_library_to_library[
                category + '.' + data_source + '.' + freq + '.' + cut]

        filtered_tickers = []

        for tick in tickers:
            if re.search(filter, tick):
                filtered_tickers.append(tick)

        return filtered_tickers

    @staticmethod
    def get_tickers_list_for_category(category, data_source, freq, cut):
        return ConfigManager._dict_time_series_category_tickers_library_to_library[
                category + '.' + data_source + '.' + freq + '.' + cut]

    @staticmethod
    def get_vendor_tickers_list_for_category(category, data_source, freq, cut):
        category_source_freq_cut = category + '.' + data_source + '.' + freq + '.' + cut

        return ConfigManager.get_vendor_tickers_list_for_category_str(category_source_freq_cut)

    @staticmethod
    def get_tickers_list_for_category_str(category_data_source_freq_cut):
        return ConfigManager._dict_time_series_category_tickers_library_to_library[category_data_source_freq_cut]

    @staticmethod
    def get_vendor_tickers_list_for_category_str(category_data_source_freq_cut):
        tickers = ConfigManager._dict_time_series_category_tickers_library_to_library[category_data_source_freq_cut]

        vendor_tickers = []

        for t in tickers:
            vendor_tickers.append(ConfigManager.convert_library_to_vendor_ticker_str(category_data_source_freq_cut + "." + t))

        return ConfigManager.flatten_list_of_lists(vendor_tickers)

    @staticmethod
    def convert_library_to_vendor_ticker(category, data_source, freq, cut, ticker):
        return ConfigManager._dict_time_series_tickers_list_library_to_vendor[
            category + '.' + data_source + '.' + freq + '.' + cut + '.' + ticker]

    @staticmethod
    def convert_library_to_vendor_ticker_str(category_data_source_freq_cut_ticker):
        return ConfigManager._dict_time_series_tickers_list_library_to_vendor[category_data_source_freq_cut_ticker]

    @staticmethod
    def convert_vendor_to_library_ticker(data_source, vendor_tickers):
        return ConfigManager._dict_time_series_tickers_list_vendor_to_library[
            data_source + '.' + vendor_tickers]

    @staticmethod
    def convert_vendor_to_library_field(data_source, vendor_fields):
        return ConfigManager._dict_time_series_fields_list_vendor_to_library[
            data_source + '.' + vendor_fields]

    @staticmethod
    def convert_library_to_vendor_field(data_source, fields):
        return ConfigManager._dict_time_series_fields_list_library_to_vendor[
            data_source + '.' + fields]

    @staticmethod
    def remove_duplicates_and_flatten_list(lst):
        return list(dict.fromkeys(ConfigManager.flatten_list_of_lists(lst)))

    @staticmethod
    def flatten_list_of_lists(list_of_lists):
        """Flattens lists of obj, into a single list of strings (rather than characters, which is default behavior).

        Parameters
        ----------
        list_of_lists : obj (list)
            List to be flattened

        Returns
        -------
        str (list)
        """

        if isinstance(list_of_lists, list):
            rt = []
            for i in list_of_lists:
                if isinstance(i, list):
                    rt.extend(ConfigManager.flatten_list_of_lists(i))
                else:
                    rt.append(i)

            return rt

        return list_of_lists


## test function
if __name__ == '__main__':
    logger = LoggerManager().getLogger(__name__)

    data_constants = DataConstants(override_fields={'use_cache_compression' : False})

    print(data_constants.use_cache_compression)

    cm = ConfigManager().get_instance()

    categories = cm.get_categories_from_fields()

    logger.info("Categories from fields list")
    print(categories)

    categories = cm.get_categories_from_tickers()

    logger.info("Categories from tickers list")
    print(categories)

    filter = 'events'

    categories_filtered = cm.get_categories_from_tickers_selective_filter(filter)
    logger.info("Categories from tickers list, filtered by events")
    print(categories_filtered)

    logger.info("For each category, print all tickers and fields")

    for sing in categories:
        split_sing = sing.split(".")
        category = split_sing[0]
        data_source = split_sing[1]
        freq = split_sing[2]
        cut = split_sing[3]

        logger.info("tickers for " + sing)
        tickers = cm.get_tickers_list_for_category(category, data_source, freq, cut)

        print(tickers)

        logger.info("fields for " + sing)
        fields = cm.get_fields_list_for_category(category, data_source, freq, cut)

        print(fields)

    # test the various converter mechanisms
    output = cm.convert_library_to_vendor_ticker(category='fx', data_source='bloomberg', freq='daily', cut='TOK', ticker='USDJPY')

    print(output)

    output = cm.convert_vendor_to_library_ticker(
        data_source='bloomberg', vendor_tickers='EURUSD CMPT Curncy')

    print(output)

    output = cm.convert_vendor_to_library_field(
        data_source='bloomberg', vendor_fields='PX_LAST')

    print(output)

    output = cm.convert_library_to_vendor_field(
        data_source='bloomberg', vendor_fields='close')

    print(output)

    print(DataConstants().use_cache_compression)



