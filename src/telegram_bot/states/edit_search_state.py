from aiogram.fsm.state import State, StatesGroup

class EditSearchState(StatesGroup):
    selecting_field = State()      # Field selection menu
    editing_query = State()
    editing_price_min = State()
    editing_price_max = State()