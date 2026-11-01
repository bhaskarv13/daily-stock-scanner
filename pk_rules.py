"""Selected PKScreener screening functions, copied without logic changes.
Upstream: https://github.com/pkjmesra/PKScreener
Commit: ab4212355e2442e7c8f5430d53fa3f56ea5af3b8
Original copyright (c) 2023 pkjmesra, MIT license (see PKSCREENER_LICENSE.txt).
This small adapter omits terminal colouring; it is not the full PKScreener app.
"""
import math
import numpy as np
class colorText:
    GREEN = FAIL = WARN = END = ""

class PKRules:
    def findBreakoutValue(
        self, df, screenDict, saveDict, daysToLookback, alreadyBrokenout=False
    ):
        if df is None or len(df) == 0:
            return False
        data = df.copy()
        data = data.fillna(0)
        data = data.replace([np.inf, -np.inf], 0)
        recent = data.head(1)
        data = data[1:]
        maxHigh = round(data.describe()["high"]["max"], 2)
        maxClose = round(data.describe()["close"]["max"], 2)
        recentClose = round(recent["close"].iloc[0], 2)
        if np.isnan(maxClose) or np.isnan(maxHigh):
            saveDict["Breakout"] = "BO: 0 R: 0"
            screenDict["Breakout"] = (
                colorText.WARN + "BO: 0 R: 0" + colorText.END
            )
            # self.default_logger.info(
            #     f'For Stock:{saveDict["Stock"]}, the breakout is unknown because max-high ({maxHigh}) or max-close ({maxClose}) are not defined.'
            # )
            return False
        if maxHigh > maxClose:
            if (maxHigh - maxClose) <= (maxHigh * 2 / 100):
                saveDict["Breakout"] = "BO: " + str(maxClose) + " R: " + str(maxHigh)
                if recentClose >= maxClose:
                    screenDict["Breakout"] = (
                        colorText.GREEN
                        + "BO: "
                        + str(maxClose)
                        + colorText.END
                        + (colorText.GREEN if recentClose >= maxHigh else colorText.FAIL)
                        + " R: "
                        + str(maxHigh)
                        + colorText.END
                    )
                    # self.default_logger.info(
                    #     f'Stock:{saveDict["Stock"]}, has a breakout because max-high ({maxHigh}) >= max-close ({maxClose})'
                    # )
                    return True and alreadyBrokenout and self.getCandleType(recent)
                # self.default_logger.info(
                #     f'Stock:{saveDict["Stock"]}, does not have a breakout yet because max-high ({maxHigh}) < max-close ({maxClose})'
                # )
                screenDict["Breakout"] = (
                    colorText.FAIL
                    + "BO: "
                    + str(maxClose)
                    + colorText.END
                    + (colorText.GREEN if recentClose >= maxHigh else colorText.FAIL)
                    + " R: "
                    + str(maxHigh)
                    + colorText.END
                )
                return not alreadyBrokenout
            noOfHigherShadows = len(data[data.high > maxClose])
            if daysToLookback / noOfHigherShadows <= 3:
                saveDict["Breakout"] = "BO: " + str(maxHigh) + " R: 0"
                if recentClose >= maxHigh:
                    screenDict["Breakout"] = (
                        colorText.GREEN
                        + "BO: "
                        + str(maxHigh)
                        + " R: 0"
                        + colorText.END
                    )
                    # self.default_logger.info(
                    #     f'Stock:{saveDict["Stock"]}, has a breakout because recent-close ({recentClose}) >= max-high ({maxHigh})'
                    # )
                    return True and alreadyBrokenout and self.getCandleType(recent)
                # self.default_logger.info(
                #     f'Stock:{saveDict["Stock"]}, does not have a breakout yet because recent-close ({recentClose}) < max-high ({maxHigh})'
                # )
                screenDict["Breakout"] = (
                    colorText.FAIL
                    + "BO: "
                    + str(maxHigh)
                    + " R: 0"
                    + colorText.END
                )
                return not alreadyBrokenout
            saveDict["Breakout"] = "BO: " + str(maxClose) + " R: " + str(maxHigh)
            if recentClose >= maxClose:
                # self.default_logger.info(
                #     f'Stock:{saveDict["Stock"]}, has a breakout because recent-close ({recentClose}) >= max-close ({maxClose})'
                # )
                screenDict["Breakout"] = (
                    colorText.GREEN
                    + "BO: "
                    + str(maxClose)
                    + colorText.END
                    + (colorText.GREEN if recentClose >= maxHigh else colorText.FAIL)
                    + " R: "
                    + str(maxHigh)
                    + colorText.END
                )
                return True and alreadyBrokenout and self.getCandleType(recent)
            # self.default_logger.info(
            #     f'Stock:{saveDict["Stock"]}, does not have a breakout yet because recent-close ({recentClose}) < max-high ({maxHigh})'
            # )
            screenDict["Breakout"] = (
                colorText.FAIL
                + "BO: "
                + str(maxClose)
                + colorText.END
                + (colorText.GREEN if recentClose >= maxHigh else colorText.FAIL)
                + " R: "
                + str(maxHigh)
                + colorText.END
            )
            return not alreadyBrokenout
        else:
            saveDict["Breakout"] = "BO: " + str(maxClose) + " R: 0"
            if recentClose >= maxClose:
                # self.default_logger.info(
                #     f'Stock:{saveDict["Stock"]}, has a breakout because recent-close ({recentClose}) >= max-close ({maxClose})'
                # )
                screenDict["Breakout"] = (
                    colorText.GREEN
                    + "BO: "
                    + str(maxClose)
                    + " R: 0"
                    + colorText.END
                )
                return True and alreadyBrokenout and self.getCandleType(recent)
            # self.default_logger.info(
            #     f'Stock:{saveDict["Stock"]}, has a breakout because recent-close ({recentClose}) < max-close ({maxClose})'
            # )
            screenDict["Breakout"] = (
                colorText.FAIL
                + "BO: "
                + str(maxClose)
                + " R: 0"
                + colorText.END
            )
            return not alreadyBrokenout

    def getCandleType(self, dailyData):
        return bool(dailyData["close"].iloc[0] >= dailyData["open"].iloc[0])

    def validateRSI(self, df, screenDict, saveDict, minRSI, maxRSI,rsiKey="RSI"):
        if df is None or len(df) == 0:
            return False
        if rsiKey not in df.columns:
            return False
        data = df.copy()
        data = data.fillna(0)
        data = data.replace([np.inf, -np.inf], 0)
        rsi = int(data.head(1)[rsiKey].iloc[0])
        saveDict[rsiKey] = rsi
        # https://chartink.com/screener/rsi-screening
        if rsi> 0 and rsi >= minRSI and rsi <= maxRSI:  # or (rsi <= 71 and rsi >= 67):
            screenDict[rsiKey] = (
                colorText.GREEN + str(rsi) + colorText.END
            )
            return True if (rsiKey == "RSIi") else (self.validateRSI(df, screenDict, saveDict, minRSI, maxRSI,rsiKey="RSIi") or True)
        screenDict[rsiKey] = colorText.FAIL + str(rsi) + colorText.END
        # If either daily or intraday RSI comes within range?
        return False if (rsiKey == "RSIi") else (self.validateRSI(df, screenDict, saveDict, minRSI, maxRSI,rsiKey="RSIi"))

    def validateVolume(
        self, df, screenDict, saveDict, volumeRatio=2.5, minVolume=100
    ):
        if df is None or len(df) == 0:
            return False, False
        data = df.copy()
        data = data.fillna(0)
        data = data.replace([np.inf, -np.inf], 0)
        recent = data.head(1)
        # Either the rolling volume of past 20 sessions or today's volume should be > min volume
        hasMinimumVolume = (
            recent["VolMA"].iloc[0] >= minVolume
            or recent["volume"].iloc[0] >= minVolume
        )
        if recent["VolMA"].iloc[0] == 0:  # Handles Divide by 0 warning
            saveDict["volume"] = 0  # "Unknown"
            screenDict["volume"] = 0
            return False, hasMinimumVolume
        ratio = round(recent["volume"].iloc[0] / recent["VolMA"].iloc[0], 2)
        saveDict["volume"] = ratio
        if ratio >= volumeRatio and ratio != np.nan and (not math.isinf(ratio)):
            screenDict["volume"] = ratio
            return True, hasMinimumVolume
        screenDict["volume"] = ratio
        return False, hasMinimumVolume
