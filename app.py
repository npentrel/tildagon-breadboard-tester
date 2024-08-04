import app
import asyncio
import time

from app_components import clear_background, Notification
from app_components.layout import ButtonDisplay, DefinitionDisplay, LinearLayout
from events.input import BUTTON_TYPES, ButtonDownEvent
from system.eventbus import eventbus
from system.hexpansion.events import HexpansionRemovalEvent, HexpansionInsertionEvent
from system.hexpansion.config import HexpansionConfig

from machine import Pin


def string_formatter(value):
    if value is False:
        return "OFF"
    else:
        return "ON"

def string_formatter_hex(value):
    if value is None:
        return "Insert or reinsert hexpansion."
    else:
        return "Hexpansion " + {
            1: "One",
            2: "Two",
            3: "Three",
            4: "Four",
            5: "Five",
            6: "Six"
        }[value]

class BreadboardDemo(app.App):
    def __init__(self):
        self.layout = LinearLayout(items=[DefinitionDisplay("", "")])
        self.notification = None
        self.options = [
            ("hexpansion", "Hexpansion", string_formatter_hex, None),
            ("ls_1", "2 eGPIO (LS_1)", string_formatter, None),
            ("ls_2", "3 eGPIO (LS_2)", string_formatter, None),
            ("ls_3", "7 eGPIO (LS_3)", string_formatter, None),
            ("ls_4", "8 eGPIO (LS_4)", string_formatter, None),
            ("ls_5", "9 eGPIO (LS_5)", string_formatter, None),
            ("hs_1", "12 GPIO (HS_1)", string_formatter, None),
            ("hs_2", "13 GPIO (HS_2)", string_formatter, None),
            ("hs_3", "18 GPIO (HS_3)", string_formatter, None),
            ("hs_4", "19 GPIO (HS_4)", string_formatter, None)
        ]
        self.app_settings = {
            "hexpansion": None,
            "ls_1": False,
            "ls_2": False,
            "ls_3": False,
            "ls_4": False,
            "ls_5": False,
            "hs_1": False,
            "hs_2": False,
            "hs_3": False,
            "hs_4": False
        }
        self.pins = {
            "ls_1": None,
            "ls_2": None,
            "ls_3": None,
            "ls_4": None,
            "ls_5": None,
            "hs_1": None,
            "hs_2": None,
            "hs_3": None,
            "hs_4": None
        }

        eventbus.on_async(ButtonDownEvent, self._button_handler, self)
        eventbus.on_async(HexpansionInsertionEvent, self._handle_hexpansion_insertion, self)
        eventbus.on_async(HexpansionRemovalEvent, self._handle_hexpansion_removal, self)

    async def _handle_hexpansion_insertion(self, event):
        self.hexpansion_config = HexpansionConfig(event.port)
        self.app_settings["hexpansion"] = self.hexpansion_config.port
        self._init_pin_values()
        await self.update_values()

    async def _handle_hexpansion_removal(self, event):
        self.hexpansion_config = None
        self.app_settings["hexpansion"] = None
        await self.update_values()

    def _init_pin_values(self):
        # eGPIO pins
        self.pins["ls_1"] = self.hexpansion_config.ls_pin[0]
        self.pins["ls_1"].init(self.pins["ls_1"].OUT)
        self.pins["ls_2"] = self.hexpansion_config.ls_pin[1]
        self.pins["ls_2"].init(self.pins["ls_2"].OUT)
        self.pins["ls_3"] = self.hexpansion_config.ls_pin[2]
        self.pins["ls_3"].init(self.pins["ls_3"].OUT)
        self.pins["ls_4"] = self.hexpansion_config.ls_pin[3]
        self.pins["ls_4"].init(self.pins["ls_4"].OUT)
        self.pins["ls_5"] = self.hexpansion_config.ls_pin[4]
        self.pins["ls_5"].init(self.pins["ls_5"].OUT)
        # GPIO pins
        self.pins["hs_1"] = self.hexpansion_config.pin[0]
        self.pins["hs_1"].init(self.pins["hs_1"].OUT)
        self.pins["hs_2"] = self.hexpansion_config.pin[1]
        self.pins["hs_2"].init(self.pins["hs_2"].OUT)
        self.pins["hs_3"] = self.hexpansion_config.pin[2]
        self.pins["hs_3"].init(self.pins["hs_3"].OUT)
        self.pins["hs_4"] = self.hexpansion_config.pin[3]
        self.pins["hs_4"].init(self.pins["hs_4"].OUT)


    async def _read_values(self):
        if not self.hexpansion_config:
            return
        # eGPIO pins
        for id in ["ls_1", "ls_2", "ls_3", "ls_4", "ls_5", "hs_1", "hs_2", "hs_3", "hs_4"]:
            self.app_settings[id] = bool(self.pins[id].value())

    async def _button_handler(self, event):
        layout_handled = await self.layout.button_event(event)
        if not layout_handled:
            if BUTTON_TYPES["CANCEL"] in event.button:
                self.minimise()

    async def update_values(self):
        await self._read_values()
        for item in self.layout.items:
            if isinstance(item, DefinitionDisplay):
                for id, label, formatter, _ in self.options:
                    if item.label == label:
                        if id in self.app_settings.keys():
                            value = self.app_settings[id
                            ]
                        else:
                            value = ""
                        item.value = formatter(value)

    async def create_selector_handler(self, id, render_update):
        async def _button_selector_event(event):
            if not self.hexpansion_config:
                self.notification = Notification("No hexpansion! Cannot change value.")
            else:
                value = self.app_settings[id]
                if BUTTON_TYPES["CONFIRM"] in event.button:
                    print("Reading pin before toggle", id, self.pins[id].value())
                    # toggle pin high or low
                    self.pins[id].value(not self.pins[id].value())
                    print("Reading pin after toggle", id, self.pins[id].value())
                    await self.update_values()
                    await render_update()
                    return True
            return False
        return _button_selector_event

    async def run(self, render_update):
        last_time = time.ticks_ms()
        while True:
            self.layout.items = []

            for id, label, formatter, _ in self.options:
                entry = DefinitionDisplay(label, formatter(self.app_settings[id
                    ]))
                self.layout.items.append(entry)

                if id.startswith("ls") or id.startswith("hs"):
                    handler = await self.create_selector_handler(id, render_update)
                    entry = ButtonDisplay(
                        "Change", button_handler= handler
                    )
                    self.layout.items.append(entry)
            while True:
                cur_time = time.ticks_ms()
                delta_ticks = time.ticks_diff(cur_time, last_time)
                if self.update(delta_ticks) is not False:
                    await render_update()
                else:
                    await asyncio.sleep(0.05)
                last_time = cur_time

    def update(self, delta):
        if self.notification:
            self.notification.update(delta)
        return True

    def draw(self, ctx):
        clear_background(ctx)
        self.layout.draw(ctx)
        if self.notification:
            self.notification.draw(ctx)

__app_export__ = BreadboardDemo
