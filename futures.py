import datetime
from tkinter import *
from ib_insync.contract import *  # noqa
from ib_insync import *
from twilio.rest import Client
import json
import datetime as dt


def start_gui():
    import asyncio
    import tkinter as tk
    import btalib

    from ib_insync import IB, util

    util.patchAsyncio()

    class TkApp:

        def on_new_bar(self, bars: BarDataList, has_new_bar: bool):

            monetary_trade_size = self.order_size_entry.get()
            short_ma_timeframe = int(self.short_ma_entry.get())
            long_ma_timeframe = int(self.long_ma_entry.get())
            trailing_amount = float(self.trailing_stop_distance.get())/1.0




            if has_new_bar:
                now = datetime.datetime.now()
                dt_string = now.strftime("%H:%M:%S")

                print(dt_string, "New Bar Received!")
                print("In long trade", self.in_long_trade)
                print("In short trade", self.in_short_trade)
                # Getting new Information with new every new bar

                # Creating Dataframe using latest returned stock information

                long_crossover_occured = False
                short_crossover_occured = False


                df = util.df(bars)
                print(df.head())
                # checking wether a crossover has occured by taking the current candle close moving average and the previous candle close moving average,
                # checking on the one hand if we are in a long or short signal environment, and wether we have had a crossover on the last bar rather than
                # returning true anytime the short SMA is above the long SMA.
                # moving_average_type = self.moving_average_type.get()
                # if not moving_average_type:
                #     moving_average_type = "sma"


                current_short_ma, previous_short_ma = self.simple_moving_average(df, short_ma_timeframe)
                current_long_ma, previous_long_ma = self.simple_moving_average(df, long_ma_timeframe)

                print(current_long_ma, current_long_ma)
                print(previous_short_ma, previous_long_ma)

                # else:
                #     current_short_ma, previous_short_ma = self.exponential_moving_average(df, short_ma_timeframe)
                #     current_long_ma, previous_long_ma = self.exponential_moving_average(df, long_ma_timeframe)

                # Checking if a MA crossover occured

                if current_short_ma > current_long_ma and previous_short_ma < previous_long_ma:
                    long_crossover_occured = True
                    print("long crossover")

                if current_short_ma < current_long_ma and previous_short_ma > previous_long_ma:
                    short_crossover_occured = True
                    print("short crossover")

                # If Long and Short Instrument are the same we aim to either go long on a buy signal and short on a
                # sell signal rather than buying either a short or long instrument.

                current_50_ma, previous_50_ma = self.exponential_moving_average(df, 50)


                if self.underlying_instrument in [i.contract for i in self.ib.positions()]:
                    print("In long trade", self.in_long_trade)
                    print("In short trade", self.in_short_trade)
                    current_price = self.get_current_price(self.underlying_instrument)
                    order_quantity = int(monetary_trade_size)

                    print("In Loop 2")

                    if short_crossover_occured and self.in_long_trade:
                        self.cancel_order()

                        market_sell_order = LimitOrder("SELL", order_quantity*2, current_price)
                        sell_trade = self.ib.placeOrder(self.underlying_instrument, market_sell_order)
                        sell_trade.filledEvent += self.order_status


                        self.trailing_stop_order = Order()
                        self.trailing_stop_order.action = "BUY"
                        self.trailing_stop_order.orderType = "TRAIL"
                        self.trailing_stop_order.totalQuantity = order_quantity
                        self.trailing_stop_order.trailingPercent = trailing_amount



                        self.trailing_stop_trade = self.ib.placeOrder(self.underlying_instrument,
                                                                      self.trailing_stop_order)

                        self.trailing_stop_trade.filledEvent += self.stop_triggered

                        self.in_short_trade = True
                        self.in_long_trade = False


                    # If currently in short trade and the reverse crossover occurs a sell order is triggered


                    if long_crossover_occured and self.in_short_trade:
                        self.cancel_order()
                        market_buy_order = LimitOrder("BUY", order_quantity*2, current_price)
                        sell_trade = self.ib.placeOrder(self.underlying_instrument, market_buy_order)
                        sell_trade.filledEvent += self.order_status


                        self.trailing_stop_order = Order()
                        self.trailing_stop_order.action = "SELL"
                        self.trailing_stop_order.orderType = "TRAIL"
                        self.trailing_stop_order.totalQuantity = order_quantity
                        self.trailing_stop_order.trailingPercent = trailing_amount


                        self.trailing_stop_trade = self.ib.placeOrder(self.underlying_instrument,
                                                                      self.trailing_stop_order)

                        self.trailing_stop_trade.filledEvent += self.stop_triggered


                        self.in_long_trade = True
                        self.in_short_trade = False





                # Checking if we are currently in a position or not


                elif self.underlying_instrument not in [i.contract for i in self.ib.positions()]:

                    current_price = self.get_current_price(self.underlying_instrument)
                        # This if triggers when we are currently not in a position, hence we are waiting for a signal
                        # to either buy on a long signal or short sell the instrument on a sell signal.
                    print("In Loop 1")
                    if long_crossover_occured:

                        #If we got a buy signal we will be looking to purchase the Instrument.
                        order_quantity = int(monetary_trade_size)

                        limit_buy_order = LimitOrder("BUY", order_quantity, current_price)

                        # Creating trailing stop order to attach to the original market order

                        self.trailing_stop_order = Order()
                        self.trailing_stop_order.action = "SELL"
                        self.trailing_stop_order.orderType = "TRAIL"
                        self.trailing_stop_order.totalQuantity = order_quantity
                        self.trailing_stop_order.trailingPercent = trailing_amount

                        primary_trade = self.ib.placeOrder(self.underlying_instrument, limit_buy_order)
                        self.trailing_stop_trade = self.ib.placeOrder(self.underlying_instrument, self.trailing_stop_order)

                        primary_trade.filledEvent += self.order_status
                        self.trailing_stop_trade.filledEvent += self.stop_triggered

                        self.in_long_trade = True

                    if short_crossover_occured:

                        current_price = self.get_current_price(self.underlying_instrument)
                        order_quantity = int(monetary_trade_size)

                        limit_sell_order = LimitOrder("SELL", totalQuantity=order_quantity, lmtPrice=current_price)
                        sell_trade = self.ib.placeOrder(self.underlying_instrument, limit_sell_order)
                        sell_trade.filledEvent += self.order_status

                        self.trailing_stop_order = Order()
                        self.trailing_stop_order.action = "BUY"
                        self.trailing_stop_order.orderType = "TRAIL"
                        self.trailing_stop_order.totalQuantity = order_quantity
                        self.trailing_stop_order.trailingPercent = trailing_amount


                        primary_trade = self.ib.placeOrder(self.underlying_instrument, limit_sell_order)
                        self.trailing_stop_trade = self.ib.placeOrder(self.underlying_instrument, self.trailing_stop_order)

                        primary_trade.filledEvent += self.order_status
                        self.trailing_stop_trade.filledEvent += self.stop_triggered

                        self.in_short_trade = True




                        # If currently in long trade and the reverse crossover occurs a sell order is triggered



        def start_bot(self):

            preset_dictionary = {
                "future": self.future_name.get(),
                "expiry_month": self.future_expiry_month.get(),
                "expiry_year": self.future_expiry_year.get(),
                "order_size": self.order_size_entry.get(),
                "stop_loss": self.trailing_stop_distance.get(),
                "ma_type": self.moving_average_type.get(),
                "short_ma": self.short_ma_entry.get(),
                "long_ma": self.long_ma_entry.get(),
                "candle_timeframe" : self.candle_timeframe.get(),
            }

            with open("data.json", "w") as fp:
                json.dump(preset_dictionary, fp)

            if self.future_expiry_month.get() == "JAN":
                self.future_expiry_month.set( "01")
            elif self.future_expiry_month.get() == "FEB":
                self.future_expiry_month.set("02")
            elif self.future_expiry_month.get() == "MAR":
                self.future_expiry_month.set("03")
            elif self.future_expiry_month.get() == "APR":
                self.future_expiry_month.set("04")
            elif self.future_expiry_month.get() == "MAY":
                self.future_expiry_month.set("05")
            elif self.future_expiry_month.get() == "JUN":
                self.future_expiry_month.set("06")
            elif self.future_expiry_month.get() == "JUL":
                self.future_expiry_month.set("07")
            elif self.future_expiry_month.get() == "AUG":
                self.future_expiry_month.set("08")
            elif self.future_expiry_month.get() == "SEP":
                self.future_expiry_month.set("09")
            elif self.future_expiry_month.get() == "OCT":
                self.future_expiry_month.set("10")
            elif self.future_expiry_month.get() == "NOV":
                self.future_expiry_month.set("11")
            elif self.future_expiry_month.get() == "DEC":
                self.future_expiry_month.set("12")


            if self.future_name.get() == "Gold":
                self.future_name.set("GC")
            elif self.future_name.get() =="Nat. Gas":
                self.future_name.set("NG")
            elif self.future_name.get() == "Nasdaq":
                self.future_name.set("NQ")
            elif self.future_name.get() == "10Y T-bond":
                self.future_name.set("ZN")
            elif self.future_name.get() == "10Y Bund":
                self.future_name.set("GBL")
            elif self.future_name.get() == "ES":
                self.future_name.set("MES")

            print("STARTING TRADING BOT")
            contracts = self.ib.reqContractDetails(Future(self.future_name.get(), exchange="GLOBEX"))


            for _contract in contracts:
                year = _contract.contract.lastTradeDateOrContractMonth[0:4]
                month = _contract.contract.lastTradeDateOrContractMonth[4:6]

                if self.future_expiry_month.get() == month and self.future_expiry_year.get() == year:
                    self.underlying_instrument = _contract.contract

            if self.underlying_instrument == None:
                print("Selected Future and Expiry does not exist in this combination")
                return
            self.bar_timeframe = self.candle_timeframe.get()


            # Step 2 ----- Obtain request streaming bar data i.e. continually updated market data from the
            #              previously created contract

            data = self.ib.reqHistoricalData(
                self.underlying_instrument,
                endDateTime="",
                durationStr="5 D",
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

            try:
                with open("data.json", "r") as json_file:
                    preset_data = json.load(json_file)
            except:
                preset_data = None



            self.account_sid = "ACeea3bcfd3c752b272d74eefd3aeea3dc"
            self.auth_token = "04839f67969bbfe0bc6d772e766e0616"

            self.twilio_client = Client(self.account_sid, self.auth_token)

            self.loop = asyncio.get_event_loop()
            self.ib = IB().connect(host="127.0.0.1", port=7496, clientId=1)
            self.ib.disconnectedEvent += self.ib.connect
            self.root = tk.Tk()
            self.root.protocol('WM_DELETE_WINDOW', self._onDeleteWindow)
            self.entry = tk.Entry(self.root, width=50)
            self.label = tk.Label(self.root, text="IB Trading Bot", font=("Arial", 24))
            self.label.pack(padx=20, pady=20)
            self.first_run = True

            self.in_long_trade = False
            self.in_short_trade = False
            self.trailing_stop_order = None
            self.primary_trade_order = None
            self.primary_trade = None
            self.trailing_stop_trade = None
            self.underlying_conid = None
            self.current_position = None

            self.buttonframe = tk.Frame(self.root)
            self.buttonframe.columnconfigure(0, weight=1)
            self.buttonframe.columnconfigure(1, weight=1)
            self.buttonframe.columnconfigure(2, weight=1)

            if preset_data:
                self.future_name = StringVar(self.buttonframe)
                self.future_name.set(preset_data["future"])

                self.future_expiry_year = StringVar(self.buttonframe)
                self.future_expiry_year.set(preset_data["expiry_year"])

                self.future_expiry_month = StringVar(self.buttonframe)
                self.future_expiry_month.set(preset_data["expiry_month"])

                self.order_size_entry = tk.Entry(self.buttonframe)
                self.order_size_entry.insert(-1, preset_data["order_size"])

                self.trailing_stop_distance = tk.Entry(self.buttonframe)
                self.trailing_stop_distance.insert(-1, preset_data["stop_loss"])

                self.moving_average_type = StringVar(self.buttonframe)
                self.moving_average_type.set(preset_data["ma_type"])

                self.short_ma_entry = tk.Entry(self.buttonframe)
                self.short_ma_entry.insert(-1, preset_data["short_ma"])

                self.long_ma_entry = tk.Entry(self.buttonframe)
                self.long_ma_entry.insert(-1, preset_data["long_ma"])

                self.candle_timeframe = StringVar(self.root)
                self.candle_timeframe.set(preset_data["candle_timeframe"])



            else:
                self.future_name = StringVar(self.buttonframe)
                self.future_expiry_month = StringVar(self.buttonframe)
                self.future_expiry_year = StringVar(self.buttonframe)
                self.short_ma_entry = tk.Entry(self.buttonframe)
                self.long_ma_entry = tk.Entry(self.buttonframe)
                self.candle_timeframe = StringVar(self.root)
                self.trailing_stop_distance = tk.Entry(self.buttonframe)
                self.order_size_entry = tk.Entry(self.buttonframe)
                self.moving_average_type = StringVar(self.buttonframe)

            # self.underlying Value Conid

            underlying_label = tk.Label(self.buttonframe, text="Select Future")
            underlying_label.grid(row=0, column=0, sticky=tk.E + tk.W)



            self.underlying_entry = tk.OptionMenu(self.buttonframe, self.future_name, "MES", "DAX", "Nasdaq", "Gold", "Nat. Gas", "10Y T-bond", "10Y BUND")
            self.underlying_entry.grid(row=0, column=1)

            expiry_month_label = tk.Label(self.buttonframe, text="Select Expiry Month")
            expiry_month_label.grid(row=1, column=0, sticky=tk.E + tk.W)



            self.underlying_expiry = tk.OptionMenu(self.buttonframe, self.future_expiry_month, "JAN", "FEB", "MAR", "APR",
                                                         "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
            self.underlying_expiry.grid(row=1, column=1)

            expiry_year_label = tk.Label(self.buttonframe, text="Select Expiry Year")
            expiry_year_label.grid(row=2, column=0, sticky=tk.E + tk.W)



            self.underlying_expiry_year = tk.OptionMenu(self.buttonframe, self.future_expiry_year, "2022", "2023", "2024", "2025")
            self.underlying_expiry_year.grid(row=2, column=1)

            # self.long Instrument Conid

            spacer1 = tk.Label(self.buttonframe, text="")
            spacer1.grid(row=3, column=1)

            # self.order Size Entry

            order_size_label = tk.Label(self.buttonframe, text="Order Size (# of Contracts):")
            order_size_label.grid(row=4, column=0, sticky=tk.E + tk.W)

            self.order_size_entry.grid(row=4, column=1, sticky=tk.E + tk.W)

            spacer2 = tk.Label(self.buttonframe, text="")
            spacer2.grid(row=5, column=1)

            # self.stop Loss Entry

            stop_loss_percentage_label = tk.Label(self.buttonframe, text="Stop Loss in Percent eg 0.3")
            stop_loss_percentage_label.grid(row=6, column=0, sticky=tk.E + tk.W)

            self.trailing_stop_distance.grid(row=6, column=1, sticky=tk.E + tk.W)

            spacer3 = tk.Label(self.buttonframe, text="")
            spacer3.grid(row=7, column=1)

            self.candle_timeframe_label = tk.Label(self.buttonframe, text="Select a self.candlesize Timeframe:")
            self.candle_timeframe_label.grid(row=10, column=0, sticky=tk.E + tk.W)

            # Creating a RadioSelection for the self.candlestick Timeperiod


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


            self.short_ma_entry.grid(row=18, column=1, sticky=tk.E + tk.W)

            long_ma_label = tk.Label(self.buttonframe, text="self.long MA Timeframe (Enter a number)")
            long_ma_label.grid(row=19, column=0, sticky=tk.E + tk.W)


            self.long_ma_entry.grid(row=19, column=1, sticky=tk.E + tk.W)

            self.buttonframe.pack(padx=20, pady=20)

            start_button = tk.Button(self.root, text="Start Bot", command=self.start_bot)
            start_button.pack(padx=5, pady=5)

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
                contract, durationStr="5 D", endDateTime="",
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
            now = datetime.datetime.now()
            dt_string = now.strftime("%H:%M:%S")

            for position in self.ib.positions():
                print(position)
                print(position.contract)
                print(position.position)
                print(position.avgCost)

            if trade.orderStatus.status == 'Filled':
                fill = trade.fills[-1]
                if fill.execution.side == "BOT":
                    action = "Bought"
                else:
                    action = "Sold"


                notification = f"Current Position:\n{dt_string} - {action} {fill.contract.symbol} {fill.execution.shares} @ {fill.execution.avgPrice}"

                if not self.current_position:
                    self.current_position = tk.Label(self.root, text=notification)
                    self.current_position.pack(padx=5, pady=5)
                    self.root.update()
                else:
                    self.current_position = tk.Label(self.root, text=notification)
                    self.current_position.pack(padx=5, pady=5)
                    self.root.update()

                try:
                    message = self.twilio_client.messages.create(
                        body= f'FILLED TRADE:\n{fill.time} - {fill.execution.side} {fill.contract.symbol} {fill.execution.shares} @ {fill.execution.avgPrice}',
                        from_="+19593012526",
                        to="+4915167573635"

                    )

                    if len(self.ib.positions())== 0:
                        message = self.twilio_client.messages.create(
                            body=f'Currently no position.',
                            from_="+19593012526",
                            to="+4915167573635"

                        )

                    else:
                        for i in self.ib.positions():
                            name = i.contract.symbol
                            position = str(i.position)
                            message = self.twilio_client.messages.create(
                                body=f'CURRENT POSITION:\n{name} - {position} Contracts',
                                from_="+19593012526",
                                to="+4915167573635"

                            )
                except:
                    pass


        def stop_triggered (self):
            if self.in_short_trade:
                self.in_short_trade = False
            if self.in_long_trade:
                self.in_long_trade = False

        def cancel_order(self):
            # try:
            #     orders = [i for i in self.ib.orders()]
            #     if len(orders) > 0:
            #         for order in orders:
            #             self.ib.cancelOrder(order)
            # except:
            #     print("didn't work")
            self.ib.reqGlobalCancel()



    app = TkApp()
    app.run()


start_gui()