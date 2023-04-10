from tkinter import *
import tkinter as tk
import math
from ib_insync.contract import *  # noqa
from ib_insync import *


def start_gui():
    import asyncio
    import tkinter as tk
    import btalib

    from ib_insync import IB, util

    util.patchAsyncio()

    class TkApp:

        def simple_moving_average(self, df, length):

            # Function to calculate Exponential Moving Average given a ib_insync bars object and int length
            return (btalib.sma(df.close, period=length).df.iloc[-1]["sma"],
                    btalib.sma(df.close, period=length).df.iloc[-2]["sma"])

        def exponential_moving_average(self, df, length):

            # Function to calculate Exponential Moving Average given a ib_insync bars object and int length
            df = df.set_index(["date"])
            return (btalib.ema(df.close, period=length).df.iloc[-1]["ema"],
                    btalib.ema(df.close, period=length).df.iloc[-2]["ema"])

        def create_contract_conid(self, conId):
            contract = Contract(conId=conId)
            return self.ib.qualifyContracts(contract)

        def get_historical_df(self, contract, barSizeSetting):

            # Takes a financial instrument object and returns a dataframe with historical data

            bars = self.ib.reqHistoricalData(
                contract, durationStr="15 D", endDateTime="",
                barSizeSetting=barSizeSetting, whatToShow="Midpoint", useRTH=False
            )
            return util.df(bars)

        def get_current_price(self, contract):
            x = 0
            while x == 0:
                data = self.ib.reqMktData(contract)
                while data.last != data.last:
                    self.ib.sleep(0.01)
                self.ib.cancelMktData(contract)
                x += 1
            return data.last

        def get_previous_candle_close_price(self, contract):

            data = self.ib.reqHistoricalData(
                contract,
                endDateTime="",
                durationStr="5 D",
                barSizeSetting=self.bar_timeframe,
                whatToShow="MIDPOINT",
                useRTH=False,
                keepUpToDate=False
            )
            return data[-2].close

        def order_status(self, trade):
            if trade.orderStatus.status == 'Filled':
                fill = trade.fills[-1]

                print(
                    f'{fill.time} - {fill.execution.side} {fill.contract.symbol} {fill.execution.shares} @ {fill.execution.avgPrice}')

        def on_new_bar(self, bars: BarDataList, has_new_bar: bool):

            self.underlying_conid = self.underlying_entry.get()
            self.underlying_instrument = self.create_contract_conid(self.underlying_entry.get())[0]

            self.long_instrument = self.create_contract_conid(self.long_entry.get())
            self.short_instrument = self.create_contract_conid(self.short_entry.get())
            monetary_trade_size = self.order_size_entry.get()
            short_ma_timeframe = int(self.short_ma_entry.get())
            long_ma_timeframe = int(self.long_ma_entry.get())
            trailing_percent = int(self.stop_loss_percentage_entry.get())

            self.long_instrument = self.long_instrument[0]
            self.short_instrument = self.short_instrument[0]



            if has_new_bar:

                long_crossover_occured = False
                short_crossover_occured = False

                print("New Bar Received!")
                # Getting new Information with new every new bar

                # Creating Dataframe using latest returned stock information

                df = util.df(bars)

                # checking wether a crossover has occured by taking the current candle close moving average and the previous candle close moving average,
                # checking on the one hand if we are in a long or short signal environment, and wether we have had a crossover on the last bar rather than
                # returning true anytime the short SMA is above the long SMA.
                moving_average_type = self.moving_average_type.get()
                if not moving_average_type:
                    moving_average_type = "sma"
                current_50_sma, previous_50_sma = self.simple_moving_average(df, 50)

                if moving_average_type == "sma":
                    current_short_ma, previous_short_ma = self.simple_moving_average(df, short_ma_timeframe)
                    current_long_ma, previous_long_ma = self.simple_moving_average(df, long_ma_timeframe)

                else:
                    current_short_ma, previous_short_ma = self.exponential_moving_average(df, short_ma_timeframe)
                    current_long_ma, previous_long_ma = self.exponential_moving_average(df, long_ma_timeframe)

                print(f"Current Short MA: {current_short_ma}, current long MA: {current_long_ma}")
                print(f"Previous Short MA: {previous_short_ma}, previous long MA: {previous_long_ma}")

                # Checking if a MA crossover occured

                if current_short_ma > current_long_ma and previous_short_ma < previous_long_ma:
                    long_crossover_occured = True
                    print("LONG SMA/SMA CROSSOVER OCCURED")

                if current_short_ma < current_long_ma and previous_short_ma > previous_long_ma:
                    short_crossover_occured = True
                    print("SHORT SMA/SMA CROSSOVER OCCURED")

                # Checking if Price/50SMA crossover occured

                if self.get_current_price(
                        self.underlying_instrument) > current_50_sma > self.get_previous_candle_close_price(
                        self.underlying_instrument):
                    long_crossover_occured = True
                    print("LONG 50SMA CROSSOVER OCCURED")

                if self.get_current_price(
                        self.underlying_instrument) < current_50_sma < self.get_previous_candle_close_price(
                        self.underlying_instrument):
                    short_crossover_occured = True
                    print("SHORT 50SMA CROSSOVER OCCURED")


                # If Long and Short Instrument are the same we aim to either go long on a buy signal and short on a
                # sell signal rather than buying either a short or long instrument.




                        # If currently in long trade and the reverse crossover occurs a sell order is triggered

                if self.long_instrument in [i.contract for i in self.ib.positions()] or self.short_instrument in [i.contract for i in self.ib.positions()]:

                        current_price = self.get_current_price(self.long_instrument)
                        order_quantity = int(monetary_trade_size)

                        if short_crossover_occured:
                            market_sell_order = MarketOrder("SELL", order_quantity)
                            sell_trade = self.ib.placeOrder(self.long_instrument, market_sell_order)
                            sell_trade.filledEvent += self.order_status
                            self.ib.cancelOrder(self.trailing_stop_trade)

                            limit_buy_order = LimitOrder("BUY", order_quantity, current_price)

                            # Creating trailing stop order to attach to the original market order

                            self.trailing_stop_order = Order()
                            self.trailing_stop_order.action = "SELL"
                            self.trailing_stop_order.orderType = "TRAIL"
                            self.trailing_stop_order.totalQuantity = order_quantity
                            self.trailing_stop_order.trailingPercent = trailing_percent

                            primary_trade = self.ib.placeOrder(self.short_instrument, limit_buy_order)
                            self.trailing_stop_trade = self.ib.placeOrder(self.short_instrument,
                                                                          self.trailing_stop_order)

                            primary_trade.filledEvent += self.order_status
                            self.trailing_stop_trade.filledEvent += self.order_status

                            self.in_short_trade = True

                    # If currently in short trade and the reverse crossover occurs a sell order is triggered

                        elif long_crossover_occured:
                            market_sell_order = MarketOrder("SELL", order_quantity)
                            sell_trade = self.ib.placeOrder(self.short_instrument, market_sell_order)
                            sell_trade.filledEvent += self.order_status
                            self.ib.cancelOrder(self.trailing_stop_order)

                            current_price = self.get_current_price(self.long_instrument)
                            order_quantity = int(monetary_trade_size)

                            # Creating limit Order to buy X number of Vehicle to full out the predefined Order Size in Dollars at its current price
                            limit_buy_order = LimitOrder("BUY", order_quantity, current_price)

                            # Creating trailing stop order to attach to the original market order

                            self.trailing_stop_order = Order()
                            self.trailing_stop_order.action = "SELL"
                            self.trailing_stop_order.orderType = "TRAIL"
                            self.trailing_stop_order.totalQuantity = order_quantity
                            self.trailing_stop_order.trailingPercent = trailing_percent

                            primary_trade = self.ib.placeOrder(self.long_instrument, limit_buy_order)
                            self.trailing_stop_trade = self.ib.placeOrder(self.long_instrument,
                                                                          self.trailing_stop_order)

                            primary_trade.filledEvent += self.order_status
                            self.trailing_stop_trade.filledEvent += self.order_status

                            self.in_long_trade = True



                # Checking if currently in a trade to decide whether to monitor for buy or sell signa

                else:
                        # Currently not in a trade, hence looking for Signal to go long or short

                    if long_crossover_occured:
                        print(
                            "+++++++++++++++++++++++++++++++ Long Crossover Occured ++++++++++++++++++++++++++++++++++")
                        # Checking for the condition that the short SMA has risen over the long SMA and was previously below

                        current_price = self.get_current_price(self.long_instrument)
                        order_quantity = int(monetary_trade_size)

                        # Creating limit Order to buy X number of Vehicle to full out the predefined Order Size in Dollars at its current price
                        limit_buy_order = LimitOrder("BUY", order_quantity, current_price)

                        # Creating trailing stop order to attach to the original market order

                        self.trailing_stop_order = Order()
                        self.trailing_stop_order.action = "SELL"
                        self.trailing_stop_order.orderType = "TRAIL"
                        self.trailing_stop_order.totalQuantity = order_quantity
                        self.trailing_stop_order.trailingPercent = trailing_percent

                        primary_trade = self.ib.placeOrder(self.long_instrument, limit_buy_order)
                        self.trailing_stop_trade = self.ib.placeOrder(self.long_instrument, self.trailing_stop_order)

                        primary_trade.filledEvent += self.order_status
                        self.trailing_stop_trade.filledEvent += self.order_status

                        self.in_long_trade = True

                    elif short_crossover_occured:
                        print(
                            "+++++++++++++++++++++++++++++++ Short Crossover Occured ++++++++++++++++++++++++++++++++++")
                        current_price = self.get_current_price(self.short_instrument)
                        order_quantity = int(monetary_trade_size)

                        # Creating limit Order to buy X number of Vehicle to full out the predefined Order Size in Dollars at its current price

                        limit_buy_order = LimitOrder("BUY", order_quantity, current_price)

                        # Creating trailing stop order to attach to the original market order

                        self.trailing_stop_order = Order()
                        self.trailing_stop_order.action = "SELL"
                        self.trailing_stop_order.orderType = "TRAIL"
                        self.trailing_stop_order.totalQuantity = order_quantity
                        self.trailing_stop_order.trailingPercent = trailing_percent

                        primary_trade = self.ib.placeOrder(self.short_instrument, limit_buy_order)
                        self.trailing_stop_trade = self.ib.placeOrder(self.short_instrument, self.trailing_stop_order)

                        primary_trade.filledEvent += self.order_status
                        self.trailing_stop_trade.filledEvent += self.order_status

                        self.in_short_trade = True

        def start_bot(self):

            print("STARTING TRADING BOT")

            self.underlying_conid = self.underlying_entry.get()
            self.bar_timeframe = self.candle_timeframe.get()

            self.underlying_instrument = self.create_contract_conid(self.underlying_conid)

            # Step 2 ----- Obtain request streaming bar data i.e. continually updated market data from the
            #              previously created contract

            data = self.ib.reqHistoricalData(
                self.underlying_instrument[0],
                endDateTime="",
                durationStr="10 D",
                barSizeSetting=self.bar_timeframe,
                whatToShow="MIDPOINT",
                useRTH=False,
                keepUpToDate=True
            )

            bot_running_label = tk.Label(self.root, text="Bot is Currently Active")
            bot_running_label.pack(padx= 10, pady= 10)

            # Adding Callback to run the Trading Execution function with every new bar received from Interactive Brokers

            data.updateEvent += self.on_new_bar

        def run(self):
            self._onTimeout()
            self.loop.run_forever()

        def _onTimeout(self):
            self.root.update()
            self.loop.call_later(0.03, self._onTimeout)

        def _onDeleteWindow(self):
            self.loop.stop()

        def __init__(self):
            self.loop = asyncio.get_event_loop()
            self.ib = IB().connect(host="127.0.0.1", port=7496, clientId=1)
            self.root = tk.Tk()
            self.root.protocol('WM_DELETE_WINDOW', self._onDeleteWindow)
            self.entry = tk.Entry(self.root, width=50)
            self.label = tk.Label(self.root, text="IB Trading Bot", font=("Arial", 24))
            self.label.pack(padx=20, pady=20)
            self.first_run = True

            self.underlying_instrument = None
            self.bar_timeframe = None
            self.trailing_stop_trade = None

            self.in_long_trade = False
            self.in_short_trade = False
            self.trailing_stop_order = None
            self.primary_trade_order = None
            self.primary_trade = None
            self.trailing_stop_trade = None
            self.underlying_conid = None

            self.buttonframe = tk.Frame(self.root)
            self.buttonframe.columnconfigure(0, weight=1)
            self.buttonframe.columnconfigure(1, weight=1)
            self.buttonframe.columnconfigure(2, weight=1)

            # self.underlying Value Conid

            underlying_label = tk.Label(self.buttonframe, text="underlying Value ConID:")
            underlying_label.grid(row=0, column=0, sticky=tk.E + tk.W)

            self.underlying_entry = tk.Entry(self.buttonframe)
            self.underlying_entry.insert(END, "756733")
            self.underlying_entry.grid(row=0, column=1, sticky=tk.E + tk.W)

            # self.long Instrument Conid

            long_label = tk.Label(self.buttonframe, text="long Instrument ConID:")
            long_label.grid(row=1, column=0, sticky=tk.E + tk.W)

            self.long_entry = tk.Entry(self.buttonframe)
            self.long_entry.insert(END, "564053330")
            self.long_entry.grid(row=1, column=1, sticky=tk.E + tk.W)

            # self.short Instrument Conid

            short_label = tk.Label(self.buttonframe, text="short Instrument ConID:")
            short_label.grid(row=2, column=0, sticky=tk.E + tk.W)

            self.short_entry = tk.Entry(self.buttonframe)
            self.short_entry.insert(END, "547377772")
            self.short_entry.grid(row=2, column=1, sticky=tk.E + tk.W)

            spacer1 = tk.Label(self.buttonframe, text="")
            spacer1.grid(row=3, column=1)

            # self.order Size Entry

            order_size_label = tk.Label(self.buttonframe, text="order Size (# of Contracts):")
            order_size_label.grid(row=4, column=0, sticky=tk.E + tk.W)

            self.order_size_entry = tk.Entry(self.buttonframe)
            self.order_size_entry.grid(row=4, column=1, sticky=tk.E + tk.W)

            spacer2 = tk.Label(self.buttonframe, text="")
            spacer2.grid(row=5, column=1)

            # self.stop Loss Entry

            stop_loss_percentage_label = tk.Label(self.buttonframe, text="self.stop Loss in %")
            stop_loss_percentage_label.grid(row=6, column=0, sticky=tk.E + tk.W)

            self.stop_loss_percentage_entry = tk.Entry(self.buttonframe)
            self.stop_loss_percentage_entry.grid(row=6, column=1, sticky=tk.E + tk.W)

            spacer3 = tk.Label(self.buttonframe, text="")
            spacer3.grid(row=7, column=1)

            self.candle_timeframe_label = tk.Label(self.buttonframe, text="Select a self.candlesize Timeframe:")
            self.candle_timeframe_label.grid(row=10, column=0, sticky=tk.E + tk.W)

            # Creating a RadioSelection for the self.candlestick Timeperiod

            self.candle_timeframe = StringVar(self.root)
            self.candle_timeframe.set(None)

            min1_radio = tk.Radiobutton(self.buttonframe, text="1 Min.", variable=self.candle_timeframe, value="1 min")
            min1_radio = min1_radio.grid(row=8, column=1)

            min5_radio = tk.Radiobutton(self.buttonframe, text="5 Min.", variable=self.candle_timeframe, value="5 mins")
            min5_radio = min5_radio.grid(row=9, column=1)

            min10_radio = tk.Radiobutton(self.buttonframe, text="10 Min.", variable=self.candle_timeframe,
                                         value="10 mins")
            min10_radio = min10_radio.grid(row=10, column=1)

            min15_radio = tk.Radiobutton(self.buttonframe, text="15 Min.", variable=self.candle_timeframe,
                                         value="15 mins")
            min15_radio = min15_radio.grid(row=11, column=1)

            min30_radio = tk.Radiobutton(self.buttonframe, text="30 Min.", variable=self.candle_timeframe,
                                         value="30 mins")
            min30_radio = min30_radio.grid(row=12, column=1)

            spacer4 = tk.Label(self.buttonframe, text="")
            spacer4.grid(row=13, column=1)

            # Creating Radio to Choose type of moving average

            self.moving_average_type = StringVar()

            ma_type_label = tk.Label(self.buttonframe, text="Select a Moving Average")
            ma_type_label.grid(row=14, column=0)

            sma_radio = tk.Radiobutton(self.buttonframe, text="Simple Moving Average",
                                       variable=self.moving_average_type,
                                       value="sma")
            sma_radio.grid(row=15, column=1)

            ema_radio = tk.Radiobutton(self.buttonframe, text="Exponential Moving Average",
                                       variable=self.moving_average_type,
                                       value="ema")
            ema_radio.grid(row=16, column=1)

            spacer5 = tk.Label(self.buttonframe, text="")
            spacer5.grid(row=17, column=1)

            # Creating Entries for the Moving Average Timeframe

            short_ma_label = tk.Label(self.buttonframe, text="self.short MA Timeframe (Enter a number)")
            short_ma_label.grid(row=18, column=0, sticky=tk.E + tk.W)

            self.short_ma_entry = tk.Entry(self.buttonframe)
            self.short_ma_entry.grid(row=18, column=1, sticky=tk.E + tk.W)

            long_ma_label = tk.Label(self.buttonframe, text="self.long MA Timeframe (Enter a number)")
            long_ma_label.grid(row=19, column=0, sticky=tk.E + tk.W)

            self.long_ma_entry = tk.Entry(self.buttonframe)
            self.long_ma_entry.grid(row=19, column=1, sticky=tk.E + tk.W)

            self.buttonframe.pack(padx=20, pady=20)

            start_button = tk.Button(self.root, text="Start Bot", command=self.start_bot)
            start_button.pack(padx=5, pady=5)

            # positions_button = tk.Button(self.root, text="Show Current Position(s)")
            # positions_button.pack(padx=5, pady=5)
            #
            # stop_button = tk.Button(self.root, text="stop Bot")
            # stop_button.pack(padx=5, pady=5)
            #
            # stop_bot_close_position_button = tk.Button(self.root, text="Close Position(s) and stop Bot ")
            # stop_bot_close_position_button.pack(padx=5, pady=5)

    app = TkApp()
    app.run()


start_gui()