# library logger
from qtrader.framework.logger import logger
# library VAR simulator
from qtrader.simulation import VAR as _VAR
# library pandas cleaner
from qtrader.utils.pandas import clean

# scientific computing
import numpy as np
import pandas as pd

import os
import typing

# market data provider
import quandl
quandl.ApiConfig.api_key = os.environ.get('QUANDL_API_KEY')


class Finance:
    """Market Data Wrapper."""

    _col = 'Adj. Close'

    @classmethod
    def _get(cls,
             ticker: str,
             **kwargs) -> typing.Optional[pd.DataFrame]:
        """Helper method for `quandl.get`.

        Parameters
        ----------
        ticker: str
            Ticker name.
        **kwargs: dict
            Arguments for `quandl.get`.

        Returns
        -------
        df: pandas.DataFrame
            Market data for `ticker`.
        """
        try:
            return quandl.get(f'WIKI/{ticker}', **kwargs)
        except:
            logger.warn(f'failed to fetch market data for {ticker}')
            return None

    @classmethod
    def _csv(cls,
             root: str,
             tickers: typing.Union[str, typing.List[str]]):
        """Helper method for loading prices from CSV files.

        Parameters
        ----------
        root: str
            Path of CSV file.
        ticker: str
            Ticker name.

        Returns
        -------
        cache: pandas.Series | pandas.DataFrame
            Cached data from CSV.
        """
        df = pd.read_csv(root, index_col='Date',
                         parse_dates=True).sort_index(ascending=True)
        union = [ticker for ticker in tickers if ticker in df.columns]
        return df[union]

    @classmethod
    def Returns(cls,
                tickers: typing.List[str],
                start_date: str = None,
                end_date: str = None,
                freq: str = 'B',
                csv: str = None):
        """Get returns for `tickers`.

        Parameters
        ----------
        tickers: list
            List of ticker names.
        start_date: str, optional
            Start date in format 'YYYY-MM-DD'.
        end_date: str, optional
            End date in format 'YYYY-MM-DD'.
        freq: str, optional
            Resampling frequency.
        csv: str, optional
            CSV file path.

        Returns
        -------
        df: pandas.DataFrame
            Table of Returns of Adjusted Close prices for `tickers`.
        """
        if isinstance(csv, str):
            return cls._csv(csv, tickers).loc[start_date:end_date]
        else:
            return cls.Prices(tickers,
                              start_date,
                              end_date,
                              freq).pct_change()[1:]

    @classmethod
    def Prices(cls,
               tickers: typing.List[str],
               start_date: str = None,
               end_date: str = None,
               freq: str = 'B',
               csv: str = None):
        """Get prices for `tickers`.

        Parameters
        ----------
        tickers: list
            List of ticker names.
        start_date: str, optional
            Start date in format 'YYYY-MM-DD'.
        end_date: str, optional
            End date in format 'YYYY-MM-DD'.
        freq: str, optional
            Resampling frequency.
        csv: str, optional
            CSV file path.

        Returns
        -------
        df: pandas.DataFrame | pandas.Series
            Table of Adjusted Close prices for `tickers`.
        """
        if isinstance(csv, str):
            return cls._csv(csv, tickers).loc[start_date:end_date]
        # tmp dictionary of panda.Series
        data = {}
        for ticker in tickers:
            tmp_df = cls._get(
                ticker, start_date=start_date, end_date=end_date)
            # successful data fetchinf
            if tmp_df is not None:
                data[ticker] = tmp_df[cls._col]
        # dict to pandas.DataFrame
        df = pd.DataFrame(data)
        return df.sort_index(ascending=True).resample(freq).last()

    @classmethod
    def SP500(cls, return_prices_returns: bool = False, **kwargs):
        # fetch table of constituents
        sp500 = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
                             header=0)[0]
        # keep columns of interest
        sp500 = sp500[['Ticker symbol', 'Security', 'GICS Sector']]
        # set ticker as index
        sp500.set_index('Ticker symbol', inplace=True)
        # fetch prices & returns
        if return_prices_returns:
            # get tickers list
            tickers = sp500.index.tolist()
            # pass arguments to method
            prices = cls.Prices(tickers, **kwargs)
            # calculate returns
            returns = prices.pct_change()[1:]
            return sp500, prices, returns
        # ignore prices & returns
        else:
            return sp500


class VAR:
    """Vector Autoregressive Process Wrapper."""

    @classmethod
    def Returns(cls,
                tickers: typing.List[str],
                start_date: str = None,
                end_date: str = None,
                freq: str = 'B',
                csv: str = None,
                model_order: int = 2,
                return_params: bool = False):
        """Get VAR simulated returns for `tickers`.

        Parameters
        ----------
        tickers: list
            List of ticker names.
        start_date: str, optional
            Start date in format 'YYYY-MM-DD'.
        end_date: str, optional
            End date in format 'YYYY-MM-DD'.
        freq: str, optional
            Resampling frequency.
        csv: str, optional
            CSV file path.
        model_order: int, optional
            VAR model order.
        return_params: bool, optional
            Return pandas.DataFrame of model parameters.

        Returns
        -------
        df: pandas.DataFrame
            Table of Returns of Adjusted Close prices for `tickers`.
        params: pandas.DataFrame
            VAR model parameters.
        """
        df = clean(Finance.Returns(tickers, start_date, end_date, freq, csv))
        sim_df, model = _VAR(df, model_order, True)
        return (sim_df, model.params) if return_params else sim_df

    @classmethod
    def Prices(cls,
               tickers: typing.List[str],
               start_date: str = None,
               end_date: str = None,
               freq: str = 'B',
               csv: str = None,
               model_order: int = 2,
               return_params: bool = False):
        """Get prices for `tickers`.

        Parameters
        ----------
        tickers: list
            List of ticker names.
        start_date: str, optional
            Start date in format 'YYYY-MM-DD'.
        end_date: str, optional
            End date in format 'YYYY-MM-DD'.
        freq: str, optional
            Resampling frequency.
        csv: str, optional
            CSV file path.
        model_order: int, optional
            VAR model order.
        return_params: bool, optional
            Return pandas.DataFrame of model parameters.

        Returns
        -------
        df: pandas.DataFrame | pandas.Series
            Table of Adjusted Close prices for `tickers`.
        params: pandas.DataFrame
            VAR model parameters.
        """
        if return_params:
            returns, params = cls.Returns(tickers, start_date,
                                          end_date, freq, csv,
                                          model_order, return_params)
        else:
            returns = cls.Returns(tickers, start_date,
                                  end_date, freq, csv,
                                  model_order, return_params)
        prices = (clean(returns) + 1).cumprod()
        return (prices, params) if return_params else prices
