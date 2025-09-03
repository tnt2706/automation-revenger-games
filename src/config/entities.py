ENTITIES = {
    "entity": {
        "games": "games",
        "brands": "brands",
        "available_games": "available_games",
        "game_details": "game_details",
        "bet_settings": "bet_settings",
    },
    "gameClient": {
        "bets": "bets",
        "players": "players",
        "player_states": "player_states",
    },
    "mkt": {
        "trigger_templates": "trigger_templates",
    },
}


def get_table_name_entity(entity: str) -> str:
    return ENTITIES["entity"].get(entity, "")


def get_table_name_game_client(entity: str) -> str:
    return ENTITIES["gameClient"].get(entity, "")
