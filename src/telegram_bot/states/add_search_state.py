from aiogram.fsm.state import State, StatesGroup

class AddSearchState(StatesGroup):
    waiting_for_search_term = State()  # What to search
    waiting_for_price_min = State()    # Min price 
    waiting_for_price_max = State()    # Max price