from datetime import datetime, time, timedelta

import requests
import logging
import json

_LOGGER = logging.getLogger(__name__)

def check_time_in_intervals_by_weekday(data_json: dict, dt: datetime, signal_filter: str = "703D57H4530000000003|1"):
    # Mapování názvů dnů z JSON -> číslo dne v týdnu (0=Po, 6=Ne)
    den_map = {
        "Pondělí": 0,
        "Úterý": 1,
        "Středa": 2,
        "Čtvrtek": 3,
        "Pátek": 4,
        "Sobota": 5,
        "Neděle": 6
    }

    def parse_intervals(casy_str):
        """Rozdělí řetězec 'HH:MM-HH:MM; ...' na seznam (start_time, end_time)."""
        intervals = []
        for part in casy_str.split(";"):
            part = part.strip()
            if not part:
                continue
            start_str, end_str = [p.strip() for p in part.split("-")]

            def parse_time_str(tstr):
                if tstr == "24:00":
                    return time(23, 59, 59, 999999)
                return datetime.strptime(tstr, "%H:%M").time()

            start_t = parse_time_str(start_str)
            end_t = parse_time_str(end_str)
            intervals.append((start_t, end_t))
        return intervals

    def get_intervals_for_weekday(weekday):
        """Vrátí seznam intervalů pro daný den v týdnu."""
        signals = [
            s for s in data_json["data"]["signals"]
            if s["signal"] == signal_filter and den_map.get(s["den"]) == weekday
        ]
        if not signals:
            return []
        return parse_intervals(signals[0]["casy"])

    target_weekday = dt.weekday()
    target_time = dt.time()

    # 1️⃣ Nejprve zkusíme aktuální den
    intervals_today = get_intervals_for_weekday(target_weekday)

    # Kontrola, zda čas padá do intervalu dnes
    for start_t, end_t in intervals_today:
        if start_t <= target_time <= end_t:
            return True, f"{start_t.strftime('%H:%M')}-{end_t.strftime('%H:%M')}"

    # Hledání nejbližšího následujícího intervalu dnes
    future_today = [(s, e) for s, e in intervals_today if s > target_time]
    if future_today:
        nearest = min(future_today, key=lambda x: x[0])
        return False, f"{nearest[0].strftime('%H:%M')}-{nearest[1].strftime('%H:%M')}"

    # 2️⃣ Pokud už dnes není žádný interval → hledej zítřek
    next_day_dt = dt + timedelta(days=1)
    next_weekday = next_day_dt.weekday()
    intervals_next = get_intervals_for_weekday(next_weekday)

    if intervals_next:
        nearest = min(intervals_next, key=lambda x: x[0])  # první interval následujícího dne
        return False, f"{nearest[0].strftime('%H:%M')}-{nearest[1].strftime('%H:%M')}"

    return False, None

async def get_nttarifftable(hass, url, meterno):
    def blocking_post():
        response = requests.post(url, headers=headers, data=json_body)
        return response

    #url = "https://dip.cezdistribuce.cz/irj/portal/anonymous/casy-spinani?path=switch-times/signals"
    headers = {
        "Content-Type": "application/json",  # nebo "text/yaml" / "application/json"
        "Accept": "application/json"
    }

    json_body = """
    {
	    "sernr": "5100025085"
    }
    """

    #response = requests.post(url, headers=headers, data=json_body) 
    response = await hass.async_add_executor_job(blocking_post)

    if response.status_code == 200:
      return response.status_code, response.json()
    else:
      return response.status_code, response.text


    """
    if response.status_code == 200:
        data = yaml.safe_load(response.text)  # YAML → Python dict
        print(data)
    else:
        print("Chyba:", response.status_code, response.text)
    """
    