"""IANA time zone name -> POSIX TZ rule, as accepted by newlib's tzset() on the frame.
Generated from nayarsystems/posix_tz_db (MIT), zones.json, 2026-09-24.
The frame only ever stores the POSIX rule; the name is for people."""

import importlib.resources
import io
import os
import re
import struct
import time
import zoneinfo
from datetime import datetime, timezone

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

TIMEZONES: dict[str, str] = {
    "Africa/Abidjan": "GMT0",
    "Africa/Accra": "GMT0",
    "Africa/Addis_Ababa": "EAT-3",
    "Africa/Algiers": "CET-1",
    "Africa/Asmara": "EAT-3",
    "Africa/Bamako": "GMT0",
    "Africa/Bangui": "WAT-1",
    "Africa/Banjul": "GMT0",
    "Africa/Bissau": "GMT0",
    "Africa/Blantyre": "CAT-2",
    "Africa/Brazzaville": "WAT-1",
    "Africa/Bujumbura": "CAT-2",
    "Africa/Cairo": "EET-2EEST,M4.5.5/0,M10.5.4/24",
    "Africa/Casablanca": "<+01>-1",
    "Africa/Ceuta": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Africa/Conakry": "GMT0",
    "Africa/Dakar": "GMT0",
    "Africa/Dar_es_Salaam": "EAT-3",
    "Africa/Djibouti": "EAT-3",
    "Africa/Douala": "WAT-1",
    "Africa/El_Aaiun": "<+01>-1",
    "Africa/Freetown": "GMT0",
    "Africa/Gaborone": "CAT-2",
    "Africa/Harare": "CAT-2",
    "Africa/Johannesburg": "SAST-2",
    "Africa/Juba": "CAT-2",
    "Africa/Kampala": "EAT-3",
    "Africa/Khartoum": "CAT-2",
    "Africa/Kigali": "CAT-2",
    "Africa/Kinshasa": "WAT-1",
    "Africa/Lagos": "WAT-1",
    "Africa/Libreville": "WAT-1",
    "Africa/Lome": "GMT0",
    "Africa/Luanda": "WAT-1",
    "Africa/Lubumbashi": "CAT-2",
    "Africa/Lusaka": "CAT-2",
    "Africa/Malabo": "WAT-1",
    "Africa/Maputo": "CAT-2",
    "Africa/Maseru": "SAST-2",
    "Africa/Mbabane": "SAST-2",
    "Africa/Mogadishu": "EAT-3",
    "Africa/Monrovia": "GMT0",
    "Africa/Nairobi": "EAT-3",
    "Africa/Ndjamena": "WAT-1",
    "Africa/Niamey": "WAT-1",
    "Africa/Nouakchott": "GMT0",
    "Africa/Ouagadougou": "GMT0",
    "Africa/Porto-Novo": "WAT-1",
    "Africa/Sao_Tome": "GMT0",
    "Africa/Tripoli": "EET-2",
    "Africa/Tunis": "CET-1",
    "Africa/Windhoek": "CAT-2",
    "America/Adak": "HST10HDT,M3.2.0,M11.1.0",
    "America/Anchorage": "AKST9AKDT,M3.2.0,M11.1.0",
    "America/Anguilla": "AST4",
    "America/Antigua": "AST4",
    "America/Araguaina": "<-03>3",
    "America/Argentina/Buenos_Aires": "<-03>3",
    "America/Argentina/Catamarca": "<-03>3",
    "America/Argentina/Cordoba": "<-03>3",
    "America/Argentina/Jujuy": "<-03>3",
    "America/Argentina/La_Rioja": "<-03>3",
    "America/Argentina/Mendoza": "<-03>3",
    "America/Argentina/Rio_Gallegos": "<-03>3",
    "America/Argentina/Salta": "<-03>3",
    "America/Argentina/San_Juan": "<-03>3",
    "America/Argentina/San_Luis": "<-03>3",
    "America/Argentina/Tucuman": "<-03>3",
    "America/Argentina/Ushuaia": "<-03>3",
    "America/Aruba": "AST4",
    "America/Asuncion": "<-03>3",
    "America/Atikokan": "EST5",
    "America/Bahia": "<-03>3",
    "America/Bahia_Banderas": "CST6",
    "America/Barbados": "AST4",
    "America/Belem": "<-03>3",
    "America/Belize": "CST6",
    "America/Blanc-Sablon": "AST4",
    "America/Boa_Vista": "<-04>4",
    "America/Bogota": "<-05>5",
    "America/Boise": "MST7MDT,M3.2.0,M11.1.0",
    "America/Cambridge_Bay": "MST7MDT,M3.2.0,M11.1.0",
    "America/Campo_Grande": "<-04>4",
    "America/Cancun": "EST5",
    "America/Caracas": "<-04>4",
    "America/Cayenne": "<-03>3",
    "America/Cayman": "EST5",
    "America/Chicago": "CST6CDT,M3.2.0,M11.1.0",
    "America/Chihuahua": "CST6",
    "America/Costa_Rica": "CST6",
    "America/Creston": "MST7",
    "America/Cuiaba": "<-04>4",
    "America/Curacao": "AST4",
    "America/Danmarkshavn": "GMT0",
    "America/Dawson": "MST7",
    "America/Dawson_Creek": "MST7",
    "America/Denver": "MST7MDT,M3.2.0,M11.1.0",
    "America/Detroit": "EST5EDT,M3.2.0,M11.1.0",
    "America/Dominica": "AST4",
    "America/Edmonton": "MST7MDT,M3.2.0,M11.1.0",
    "America/Eirunepe": "<-05>5",
    "America/El_Salvador": "CST6",
    "America/Fort_Nelson": "MST7",
    "America/Fortaleza": "<-03>3",
    "America/Glace_Bay": "AST4ADT,M3.2.0,M11.1.0",
    "America/Godthab": "<-02>2<-01>,M3.5.0/-1,M10.5.0/0",
    "America/Goose_Bay": "AST4ADT,M3.2.0,M11.1.0",
    "America/Grand_Turk": "EST5EDT,M3.2.0,M11.1.0",
    "America/Grenada": "AST4",
    "America/Guadeloupe": "AST4",
    "America/Guatemala": "CST6",
    "America/Guayaquil": "<-05>5",
    "America/Guyana": "<-04>4",
    "America/Halifax": "AST4ADT,M3.2.0,M11.1.0",
    "America/Havana": "CST5CDT,M3.2.0/0,M11.1.0/1",
    "America/Hermosillo": "MST7",
    "America/Indiana/Indianapolis": "EST5EDT,M3.2.0,M11.1.0",
    "America/Indiana/Knox": "CST6CDT,M3.2.0,M11.1.0",
    "America/Indiana/Marengo": "EST5EDT,M3.2.0,M11.1.0",
    "America/Indiana/Petersburg": "EST5EDT,M3.2.0,M11.1.0",
    "America/Indiana/Tell_City": "CST6CDT,M3.2.0,M11.1.0",
    "America/Indiana/Vevay": "EST5EDT,M3.2.0,M11.1.0",
    "America/Indiana/Vincennes": "EST5EDT,M3.2.0,M11.1.0",
    "America/Indiana/Winamac": "EST5EDT,M3.2.0,M11.1.0",
    "America/Inuvik": "MST7MDT,M3.2.0,M11.1.0",
    "America/Iqaluit": "EST5EDT,M3.2.0,M11.1.0",
    "America/Jamaica": "EST5",
    "America/Juneau": "AKST9AKDT,M3.2.0,M11.1.0",
    "America/Kentucky/Louisville": "EST5EDT,M3.2.0,M11.1.0",
    "America/Kentucky/Monticello": "EST5EDT,M3.2.0,M11.1.0",
    "America/Kralendijk": "AST4",
    "America/La_Paz": "<-04>4",
    "America/Lima": "<-05>5",
    "America/Los_Angeles": "PST8PDT,M3.2.0,M11.1.0",
    "America/Lower_Princes": "AST4",
    "America/Maceio": "<-03>3",
    "America/Managua": "CST6",
    "America/Manaus": "<-04>4",
    "America/Marigot": "AST4",
    "America/Martinique": "AST4",
    "America/Matamoros": "CST6CDT,M3.2.0,M11.1.0",
    "America/Mazatlan": "MST7",
    "America/Menominee": "CST6CDT,M3.2.0,M11.1.0",
    "America/Merida": "CST6",
    "America/Metlakatla": "AKST9AKDT,M3.2.0,M11.1.0",
    "America/Mexico_City": "CST6",
    "America/Miquelon": "<-03>3<-02>,M3.2.0,M11.1.0",
    "America/Moncton": "AST4ADT,M3.2.0,M11.1.0",
    "America/Monterrey": "CST6",
    "America/Montevideo": "<-03>3",
    "America/Montreal": "EST5EDT,M3.2.0,M11.1.0",
    "America/Montserrat": "AST4",
    "America/Nassau": "EST5EDT,M3.2.0,M11.1.0",
    "America/New_York": "EST5EDT,M3.2.0,M11.1.0",
    "America/Nipigon": "EST5EDT,M3.2.0,M11.1.0",
    "America/Nome": "AKST9AKDT,M3.2.0,M11.1.0",
    "America/Noronha": "<-02>2",
    "America/North_Dakota/Beulah": "CST6CDT,M3.2.0,M11.1.0",
    "America/North_Dakota/Center": "CST6CDT,M3.2.0,M11.1.0",
    "America/North_Dakota/New_Salem": "CST6CDT,M3.2.0,M11.1.0",
    "America/Nuuk": "<-02>2<-01>,M3.5.0/-1,M10.5.0/0",
    "America/Ojinaga": "CST6CDT,M3.2.0,M11.1.0",
    "America/Panama": "EST5",
    "America/Pangnirtung": "EST5EDT,M3.2.0,M11.1.0",
    "America/Paramaribo": "<-03>3",
    "America/Phoenix": "MST7",
    "America/Port-au-Prince": "EST5EDT,M3.2.0,M11.1.0",
    "America/Port_of_Spain": "AST4",
    "America/Porto_Velho": "<-04>4",
    "America/Puerto_Rico": "AST4",
    "America/Punta_Arenas": "<-03>3",
    "America/Rainy_River": "CST6CDT,M3.2.0,M11.1.0",
    "America/Rankin_Inlet": "CST6CDT,M3.2.0,M11.1.0",
    "America/Recife": "<-03>3",
    "America/Regina": "CST6",
    "America/Resolute": "CST6CDT,M3.2.0,M11.1.0",
    "America/Rio_Branco": "<-05>5",
    "America/Santarem": "<-03>3",
    "America/Santiago": "<-04>4<-03>,M9.1.6/24,M4.1.6/24",
    "America/Santo_Domingo": "AST4",
    "America/Sao_Paulo": "<-03>3",
    "America/Scoresbysund": "<-02>2<-01>,M3.5.0/-1,M10.5.0/0",
    "America/Sitka": "AKST9AKDT,M3.2.0,M11.1.0",
    "America/St_Barthelemy": "AST4",
    "America/St_Johns": "NST3:30NDT,M3.2.0,M11.1.0",
    "America/St_Kitts": "AST4",
    "America/St_Lucia": "AST4",
    "America/St_Thomas": "AST4",
    "America/St_Vincent": "AST4",
    "America/Swift_Current": "CST6",
    "America/Tegucigalpa": "CST6",
    "America/Thule": "AST4ADT,M3.2.0,M11.1.0",
    "America/Thunder_Bay": "EST5EDT,M3.2.0,M11.1.0",
    "America/Tijuana": "PST8PDT,M3.2.0,M11.1.0",
    "America/Toronto": "EST5EDT,M3.2.0,M11.1.0",
    "America/Tortola": "AST4",
    "America/Vancouver": "PST8PDT,M3.2.0,M11.1.0",
    "America/Whitehorse": "MST7",
    "America/Winnipeg": "CST6CDT,M3.2.0,M11.1.0",
    "America/Yakutat": "AKST9AKDT,M3.2.0,M11.1.0",
    "America/Yellowknife": "MST7MDT,M3.2.0,M11.1.0",
    "Antarctica/Casey": "<+08>-8",
    "Antarctica/Davis": "<+07>-7",
    "Antarctica/DumontDUrville": "<+10>-10",
    "Antarctica/Macquarie": "AEST-10AEDT,M10.1.0,M4.1.0/3",
    "Antarctica/Mawson": "<+05>-5",
    "Antarctica/McMurdo": "NZST-12NZDT,M9.5.0,M4.1.0/3",
    "Antarctica/Palmer": "<-03>3",
    "Antarctica/Rothera": "<-03>3",
    "Antarctica/Syowa": "<+03>-3",
    "Antarctica/Troll": "<+00>0<+02>-2,M3.5.0/1,M10.5.0/3",
    "Antarctica/Vostok": "<+05>-5",
    "Arctic/Longyearbyen": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Asia/Aden": "<+03>-3",
    "Asia/Almaty": "<+05>-5",
    "Asia/Amman": "<+03>-3",
    "Asia/Anadyr": "<+12>-12",
    "Asia/Aqtau": "<+05>-5",
    "Asia/Aqtobe": "<+05>-5",
    "Asia/Ashgabat": "<+05>-5",
    "Asia/Atyrau": "<+05>-5",
    "Asia/Baghdad": "<+03>-3",
    "Asia/Bahrain": "<+03>-3",
    "Asia/Baku": "<+04>-4",
    "Asia/Bangkok": "<+07>-7",
    "Asia/Barnaul": "<+07>-7",
    "Asia/Beirut": "EET-2EEST,M3.5.0/0,M10.5.0/0",
    "Asia/Bishkek": "<+06>-6",
    "Asia/Brunei": "<+08>-8",
    "Asia/Chita": "<+09>-9",
    "Asia/Choibalsan": "<+08>-8",
    "Asia/Colombo": "<+0530>-5:30",
    "Asia/Damascus": "<+03>-3",
    "Asia/Dhaka": "<+06>-6",
    "Asia/Dili": "<+09>-9",
    "Asia/Dubai": "<+04>-4",
    "Asia/Dushanbe": "<+05>-5",
    "Asia/Famagusta": "EET-2EEST,M3.5.0/3,M10.5.0/4",
    "Asia/Gaza": "EET-2EEST,M3.4.4/50,M10.4.4/50",
    "Asia/Hebron": "EET-2EEST,M3.4.4/50,M10.4.4/50",
    "Asia/Ho_Chi_Minh": "<+07>-7",
    "Asia/Hong_Kong": "HKT-8",
    "Asia/Hovd": "<+07>-7",
    "Asia/Irkutsk": "<+08>-8",
    "Asia/Jakarta": "WIB-7",
    "Asia/Jayapura": "WIT-9",
    "Asia/Jerusalem": "IST-2IDT,M3.4.4/26,M10.5.0",
    "Asia/Kabul": "<+0430>-4:30",
    "Asia/Kamchatka": "<+12>-12",
    "Asia/Karachi": "PKT-5",
    "Asia/Kathmandu": "<+0545>-5:45",
    "Asia/Khandyga": "<+09>-9",
    "Asia/Kolkata": "IST-5:30",
    "Asia/Krasnoyarsk": "<+07>-7",
    "Asia/Kuala_Lumpur": "<+08>-8",
    "Asia/Kuching": "<+08>-8",
    "Asia/Kuwait": "<+03>-3",
    "Asia/Macau": "CST-8",
    "Asia/Magadan": "<+11>-11",
    "Asia/Makassar": "WITA-8",
    "Asia/Manila": "PST-8",
    "Asia/Muscat": "<+04>-4",
    "Asia/Nicosia": "EET-2EEST,M3.5.0/3,M10.5.0/4",
    "Asia/Novokuznetsk": "<+07>-7",
    "Asia/Novosibirsk": "<+07>-7",
    "Asia/Omsk": "<+06>-6",
    "Asia/Oral": "<+05>-5",
    "Asia/Phnom_Penh": "<+07>-7",
    "Asia/Pontianak": "WIB-7",
    "Asia/Pyongyang": "KST-9",
    "Asia/Qatar": "<+03>-3",
    "Asia/Qyzylorda": "<+05>-5",
    "Asia/Riyadh": "<+03>-3",
    "Asia/Sakhalin": "<+11>-11",
    "Asia/Samarkand": "<+05>-5",
    "Asia/Seoul": "KST-9",
    "Asia/Shanghai": "CST-8",
    "Asia/Singapore": "<+08>-8",
    "Asia/Srednekolymsk": "<+11>-11",
    "Asia/Taipei": "CST-8",
    "Asia/Tashkent": "<+05>-5",
    "Asia/Tbilisi": "<+04>-4",
    "Asia/Tehran": "<+0330>-3:30",
    "Asia/Thimphu": "<+06>-6",
    "Asia/Tokyo": "JST-9",
    "Asia/Tomsk": "<+07>-7",
    "Asia/Ulaanbaatar": "<+08>-8",
    "Asia/Urumqi": "<+06>-6",
    "Asia/Ust-Nera": "<+10>-10",
    "Asia/Vientiane": "<+07>-7",
    "Asia/Vladivostok": "<+10>-10",
    "Asia/Yakutsk": "<+09>-9",
    "Asia/Yangon": "<+0630>-6:30",
    "Asia/Yekaterinburg": "<+05>-5",
    "Asia/Yerevan": "<+04>-4",
    "Atlantic/Azores": "<-01>1<+00>,M3.5.0/0,M10.5.0/1",
    "Atlantic/Bermuda": "AST4ADT,M3.2.0,M11.1.0",
    "Atlantic/Canary": "WET0WEST,M3.5.0/1,M10.5.0",
    "Atlantic/Cape_Verde": "<-01>1",
    "Atlantic/Faroe": "WET0WEST,M3.5.0/1,M10.5.0",
    "Atlantic/Madeira": "WET0WEST,M3.5.0/1,M10.5.0",
    "Atlantic/Reykjavik": "GMT0",
    "Atlantic/South_Georgia": "<-02>2",
    "Atlantic/St_Helena": "GMT0",
    "Atlantic/Stanley": "<-03>3",
    "Australia/Adelaide": "ACST-9:30ACDT,M10.1.0,M4.1.0/3",
    "Australia/Brisbane": "AEST-10",
    "Australia/Broken_Hill": "ACST-9:30ACDT,M10.1.0,M4.1.0/3",
    "Australia/Currie": "AEST-10AEDT,M10.1.0,M4.1.0/3",
    "Australia/Darwin": "ACST-9:30",
    "Australia/Eucla": "<+0845>-8:45",
    "Australia/Hobart": "AEST-10AEDT,M10.1.0,M4.1.0/3",
    "Australia/Lindeman": "AEST-10",
    "Australia/Lord_Howe": "<+1030>-10:30<+11>-11,M10.1.0,M4.1.0",
    "Australia/Melbourne": "AEST-10AEDT,M10.1.0,M4.1.0/3",
    "Australia/Perth": "AWST-8",
    "Australia/Sydney": "AEST-10AEDT,M10.1.0,M4.1.0/3",
    "Etc/GMT": "GMT0",
    "Etc/GMT+0": "GMT0",
    "Etc/GMT+1": "<-01>1",
    "Etc/GMT+10": "<-10>10",
    "Etc/GMT+11": "<-11>11",
    "Etc/GMT+12": "<-12>12",
    "Etc/GMT+2": "<-02>2",
    "Etc/GMT+3": "<-03>3",
    "Etc/GMT+4": "<-04>4",
    "Etc/GMT+5": "<-05>5",
    "Etc/GMT+6": "<-06>6",
    "Etc/GMT+7": "<-07>7",
    "Etc/GMT+8": "<-08>8",
    "Etc/GMT+9": "<-09>9",
    "Etc/GMT-0": "GMT0",
    "Etc/GMT-1": "<+01>-1",
    "Etc/GMT-10": "<+10>-10",
    "Etc/GMT-11": "<+11>-11",
    "Etc/GMT-12": "<+12>-12",
    "Etc/GMT-13": "<+13>-13",
    "Etc/GMT-14": "<+14>-14",
    "Etc/GMT-2": "<+02>-2",
    "Etc/GMT-3": "<+03>-3",
    "Etc/GMT-4": "<+04>-4",
    "Etc/GMT-5": "<+05>-5",
    "Etc/GMT-6": "<+06>-6",
    "Etc/GMT-7": "<+07>-7",
    "Etc/GMT-8": "<+08>-8",
    "Etc/GMT-9": "<+09>-9",
    "Etc/GMT0": "GMT0",
    "Etc/Greenwich": "GMT0",
    "Etc/UCT": "UTC0",
    "Etc/UTC": "UTC0",
    "Etc/Universal": "UTC0",
    "Etc/Zulu": "UTC0",
    "Europe/Amsterdam": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Andorra": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Astrakhan": "<+04>-4",
    "Europe/Athens": "EET-2EEST,M3.5.0/3,M10.5.0/4",
    "Europe/Belgrade": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Berlin": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Bratislava": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Brussels": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Bucharest": "EET-2EEST,M3.5.0/3,M10.5.0/4",
    "Europe/Budapest": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Busingen": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Chisinau": "EET-2EEST,M3.5.0,M10.5.0/3",
    "Europe/Copenhagen": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Dublin": "IST-1GMT0,M10.5.0,M3.5.0/1",
    "Europe/Gibraltar": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Guernsey": "GMT0BST,M3.5.0/1,M10.5.0",
    "Europe/Helsinki": "EET-2EEST,M3.5.0/3,M10.5.0/4",
    "Europe/Isle_of_Man": "GMT0BST,M3.5.0/1,M10.5.0",
    "Europe/Istanbul": "<+03>-3",
    "Europe/Jersey": "GMT0BST,M3.5.0/1,M10.5.0",
    "Europe/Kaliningrad": "EET-2",
    "Europe/Kiev": "EET-2EEST,M3.5.0/3,M10.5.0/4",
    "Europe/Kirov": "MSK-3",
    "Europe/Lisbon": "WET0WEST,M3.5.0/1,M10.5.0",
    "Europe/Ljubljana": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/London": "GMT0BST,M3.5.0/1,M10.5.0",
    "Europe/Luxembourg": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Madrid": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Malta": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Mariehamn": "EET-2EEST,M3.5.0/3,M10.5.0/4",
    "Europe/Minsk": "<+03>-3",
    "Europe/Monaco": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Moscow": "MSK-3",
    "Europe/Oslo": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Paris": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Podgorica": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Prague": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Riga": "EET-2EEST,M3.5.0/3,M10.5.0/4",
    "Europe/Rome": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Samara": "<+04>-4",
    "Europe/San_Marino": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Sarajevo": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Saratov": "<+04>-4",
    "Europe/Simferopol": "MSK-3",
    "Europe/Skopje": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Sofia": "EET-2EEST,M3.5.0/3,M10.5.0/4",
    "Europe/Stockholm": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Tallinn": "EET-2EEST,M3.5.0/3,M10.5.0/4",
    "Europe/Tirane": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Ulyanovsk": "<+04>-4",
    "Europe/Uzhgorod": "EET-2EEST,M3.5.0/3,M10.5.0/4",
    "Europe/Vaduz": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Vatican": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Vienna": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Vilnius": "EET-2EEST,M3.5.0/3,M10.5.0/4",
    "Europe/Volgograd": "MSK-3",
    "Europe/Warsaw": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Zagreb": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Zaporozhye": "EET-2EEST,M3.5.0/3,M10.5.0/4",
    "Europe/Zurich": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Indian/Antananarivo": "EAT-3",
    "Indian/Chagos": "<+06>-6",
    "Indian/Christmas": "<+07>-7",
    "Indian/Cocos": "<+0630>-6:30",
    "Indian/Comoro": "EAT-3",
    "Indian/Kerguelen": "<+05>-5",
    "Indian/Mahe": "<+04>-4",
    "Indian/Maldives": "<+05>-5",
    "Indian/Mauritius": "<+04>-4",
    "Indian/Mayotte": "EAT-3",
    "Indian/Reunion": "<+04>-4",
    "Pacific/Apia": "<+13>-13",
    "Pacific/Auckland": "NZST-12NZDT,M9.5.0,M4.1.0/3",
    "Pacific/Bougainville": "<+11>-11",
    "Pacific/Chatham": "<+1245>-12:45<+1345>,M9.5.0/2:45,M4.1.0/3:45",
    "Pacific/Chuuk": "<+10>-10",
    "Pacific/Easter": "<-06>6<-05>,M9.1.6/22,M4.1.6/22",
    "Pacific/Efate": "<+11>-11",
    "Pacific/Enderbury": "<+13>-13",
    "Pacific/Fakaofo": "<+13>-13",
    "Pacific/Fiji": "<+12>-12",
    "Pacific/Funafuti": "<+12>-12",
    "Pacific/Galapagos": "<-06>6",
    "Pacific/Gambier": "<-09>9",
    "Pacific/Guadalcanal": "<+11>-11",
    "Pacific/Guam": "ChST-10",
    "Pacific/Honolulu": "HST10",
    "Pacific/Kiritimati": "<+14>-14",
    "Pacific/Kosrae": "<+11>-11",
    "Pacific/Kwajalein": "<+12>-12",
    "Pacific/Majuro": "<+12>-12",
    "Pacific/Marquesas": "<-0930>9:30",
    "Pacific/Midway": "SST11",
    "Pacific/Nauru": "<+12>-12",
    "Pacific/Niue": "<-11>11",
    "Pacific/Norfolk": "<+11>-11<+12>,M10.1.0,M4.1.0/3",
    "Pacific/Noumea": "<+11>-11",
    "Pacific/Pago_Pago": "SST11",
    "Pacific/Palau": "<+09>-9",
    "Pacific/Pitcairn": "<-08>8",
    "Pacific/Pohnpei": "<+11>-11",
    "Pacific/Port_Moresby": "<+10>-10",
    "Pacific/Rarotonga": "<-10>10",
    "Pacific/Saipan": "ChST-10",
    "Pacific/Tahiti": "<-10>10",
    "Pacific/Tarawa": "<+12>-12",
    "Pacific/Tongatapu": "<+13>-13",
    "Pacific/Wake": "<+12>-12",
    "Pacific/Wallis": "<+12>-12",
}

# ---------------------------------------------------------------------------
# Hand-written helpers. The table above is generated; regenerate it by
# replacing the dict literal and leave everything below in place.
# ---------------------------------------------------------------------------

# Firmware limit for the stored rule (main/config.h TIMEZONE_MAX_LEN); the
# device silently truncates anything longer, so refuse it here instead.
TIMEZONE_MAX_LEN = 64  # rules must be shorter than this

# Config-entry option remembering which IANA name the user last picked. The
# device only stores the POSIX rule and many zones share one (all of
# CET-1CEST,... is "Europe/*"), so without this the name shown back would be
# whichever zone happens to sort first.
OPTION_TIMEZONE_NAME = "timezone_name"

# hass.data key for the TimezoneRules loaded by async_setup_timezone_rules.
DATA_TIMEZONE_RULES = f"{DOMAIN}_timezone_rules"

# Shape of a POSIX TZ rule as newlib parses it:
#   std offset [dst [offset] [,start[/time],end[/time]]]
# Names are 3+ letters or a <...> quoted token; dates are Mm.w.d, Jn or n.
# The frame stores whatever it is given and hands it straight to tzset()
# without checking it (main/config_manager.c), and a rule that does not
# parse there leaves the frame silently running on UTC, so both the shape
# and the field ranges are checked here.
_TZ_NAME = r"(?:[A-Za-z]{3,}|<[A-Za-z0-9+\-]{3,}>)"
_TZ_HMS = r"[+-]?\d{1,3}(?::\d{1,2}(?::\d{1,2})?)?"
_TZ_DATE = r"(?:M\d{1,2}\.\d\.\d|J\d{1,3}|\d{1,3})"
POSIX_TZ_RE = re.compile(
    rf"^{_TZ_NAME}(?P<std>{_TZ_HMS})"
    rf"(?:{_TZ_NAME}(?P<dst>{_TZ_HMS})?"
    rf"(?:,(?P<start>{_TZ_DATE})(?:/(?P<start_time>{_TZ_HMS}))?"
    rf",(?P<end>{_TZ_DATE})(?:/(?P<end_time>{_TZ_HMS}))?)?)?$"
)
_TZ_MDATE_RE = re.compile(r"M(\d{1,2})\.(\d)\.(\d)")
PRINTABLE_ASCII_RE = re.compile(r"^[\x20-\x7E]*$")

# Shape of an IANA zone key ("America/Argentina/Buenos_Aires", "Etc/GMT+5",
# "UTC"). It is also what keeps a tz-database lookup inside the zoneinfo
# tree: no leading "/" and no "." at all, so no "..".
_IANA_KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_+\-]*(?:/[A-Za-z0-9_+\-]+)*$")

# TZif header (RFC 8536 section 3.1): magic, version, 15 reserved bytes, then
# isutcnt, isstdcnt, leapcnt, timecnt, typecnt, charcnt.
_TZIF_HEADER = struct.Struct(">4sc15x6l")
# How far ahead a footer rule is compared with the zone it stands for: at
# least this long, and to the last explicit transition when that is later.
_CHECK_HORIZON = 366 * 86400
_CHECK_STEP = 30 * 86400


def _hms_in_range(value: str, max_hours: int) -> bool:
    """True if a [+-]h[:mm[:ss]] field stays within ``max_hours`` and a clock's mm/ss."""
    parts = value.lstrip("+-").split(":")
    hours, minutes, seconds = (int(p) for p in (parts + ["0", "0"])[:3])
    return hours <= max_hours and minutes <= 59 and seconds <= 59


def _date_in_range(value: str) -> bool:
    """True if an Mm.w.d, Jn or n transition date names a real day."""
    if mdate := _TZ_MDATE_RE.fullmatch(value):
        month, week, day = (int(g) for g in mdate.groups())
        return 1 <= month <= 12 and 1 <= week <= 5 and day <= 6
    if value.startswith("J"):
        return 1 <= int(value[1:]) <= 365
    return int(value) <= 365


def validate_posix_rule(value: str) -> None:
    """Raise ValueError with a user-facing message unless ``value`` can be a POSIX rule."""
    if len(value) >= TIMEZONE_MAX_LEN:
        raise ValueError(f"Time zone rule too long (max {TIMEZONE_MAX_LEN - 1} chars): {value}")
    if not PRINTABLE_ASCII_RE.match(value):
        raise ValueError(f"Time zone rule must be printable ASCII: {value}")
    match = POSIX_TZ_RE.match(value)
    if match is None:
        raise ValueError(
            "Not a known IANA time zone name or a POSIX TZ rule "
            f"(e.g. Europe/Berlin or CET-1CEST,M3.5.0,M10.5.0/3): {value}"
        )
    fields = match.groupdict()
    in_range = (
        all(_hms_in_range(fields[k], 24) for k in ("std", "dst") if fields[k] is not None)
        and all(_date_in_range(fields[k]) for k in ("start", "end") if fields[k] is not None)
        # POSIX.1-2024 allows transition times up to +/-167 hours.
        and all(
            _hms_in_range(fields[k], 167)
            for k in ("start_time", "end_time")
            if fields[k] is not None
        )
    )
    if not in_range:
        raise ValueError(
            "Time zone rule has a field out of range (offset hours 0-24, month 1-12, "
            f"week 1-5, weekday 0-6, day 0-365 or J1-J365): {value}"
        )


def _read_tzif(key: str) -> bytes | None:
    """Raw TZif data for an IANA key from the system tz database or the tzdata package."""
    for root in zoneinfo.TZPATH:
        try:
            with open(os.path.join(root, key), "rb") as tzif:
                return tzif.read()
        except OSError:
            continue
    try:
        resource = importlib.resources.files("tzdata.zoneinfo")
        for part in key.split("/"):
            resource = resource.joinpath(part)
        return resource.read_bytes()
    except (ImportError, OSError, ValueError):
        return None


def _rule_only_tzif(rule: str) -> bytes:
    """A TZif file with no transitions, so ZoneInfo evaluates every instant by ``rule``."""
    local_time_type = struct.pack(">lbB", 0, 0, 0) + b"UTC\x00"
    header = _TZIF_HEADER.pack(b"TZif", b"2", 0, 0, 0, 0, 1, 4)
    block = header + local_time_type
    return block + block + b"\n" + rule.encode("ascii") + b"\n"


def _first_divergence(data: bytes, rule: str, transitions: list[int], now: float) -> str | None:
    """Date on which ``rule`` first gives another UTC offset than the zone, or None.

    The footer describes local time after the file's last explicit transition,
    which is not necessarily now: tzdata ships a clock change as soon as it is
    enacted, and spells out for decades transitions that follow the Islamic
    calendar. Comparing UTC offsets rather than transition lists also accepts
    files pre-expanded to 2037 ("fat" zic output), whose listed transitions
    are the rule's own, and a coming transition that only renames the offset
    (British Columbia going from PDT to year-round MST in 2026). Checked at
    now, a second either side of every coming explicit transition, and
    monthly until the last of them or a year out, whichever is later.
    """
    zone = zoneinfo.ZoneInfo.from_file(io.BytesIO(data))
    only_rule = zoneinfo.ZoneInfo.from_file(io.BytesIO(_rule_only_tzif(rule)))
    start = int(now)
    end = max([start + _CHECK_HORIZON, *transitions])
    instants = set(range(start, end, _CHECK_STEP))
    for transition in transitions:
        if transition >= start:
            instants.update((transition - 1, transition))
    for instant in sorted(instants):
        at = datetime.fromtimestamp(instant, timezone.utc)
        if at.astimezone(zone).utcoffset() != at.astimezone(only_rule).utcoffset():
            return at.date().isoformat()
    return None


def _tzif_rule(data: bytes, now: float) -> tuple[str, str | None] | None:
    """``(rule, diverges_on)`` from TZif data, or None if it has no usable rule.

    A version 2+ file ends with the POSIX TZ string newlib wants (RFC 8536
    section 3.3), which is also where the table above was generated from.
    ``diverges_on`` is the first date from now on for which that rule gets
    the zone's clock wrong (see _first_divergence), None when it never does.
    """
    try:
        magic, version, isut, isstd, leap, timecnt, typecnt, charcnt = _TZIF_HEADER.unpack_from(
            data
        )
        if magic != b"TZif" or version < b"2":
            return None
        v2 = _TZIF_HEADER.size + timecnt * 5 + typecnt * 6 + charcnt + leap * 8 + isstd + isut
        magic, _, _, _, _, timecnt, _, _ = _TZIF_HEADER.unpack_from(data, v2)
        if magic != b"TZif":
            return None
        transitions = list(struct.unpack_from(f">{timecnt}q", data, v2 + _TZIF_HEADER.size))
        parts = data.rsplit(b"\n", 2)
        if len(parts) != 3 or parts[2] != b"":
            return None
        rule = parts[1].decode("ascii")  # UnicodeDecodeError is a ValueError
        validate_posix_rule(rule)
        return rule, _first_divergence(data, rule, transitions, now)
    except (struct.error, ValueError, OverflowError, OSError):
        return None


def posix_rule_from_tzif(key: str, now: float | None = None) -> tuple[str, str | None] | None:
    """``(rule, diverges_on)`` for an IANA key, or None if the tz database has no such zone.

    Home Assistant resolves its own time zone from the same files, so any
    zone it can be configured for is found here, the bare "UTC" of a fresh
    install and links such as "US/Pacific" included. Blocking I/O: call
    through the executor.
    """
    if not _IANA_KEY_RE.match(key):
        return None
    data = _read_tzif(key)
    return None if data is None else _tzif_rule(data, time.time() if now is None else now)


def _build_rule_to_name(rules: dict[str, str]) -> dict[str, str]:
    """First name for each rule, preferring the zone named after the rule.

    Table order is alphabetical, which would make the default "UTC0" read
    back as "Etc/UCT" and "GMT0" as "Africa/Abidjan"; a zone whose last path
    component is the rule's own abbreviation ("Etc/UTC", "Etc/GMT") wins.
    """
    reverse: dict[str, str] = {}
    by_abbreviation: set[str] = set()
    for name, rule in rules.items():
        abbreviation = re.match(r"[A-Za-z]+", rule)
        if (
            abbreviation
            and name.rsplit("/", 1)[-1] == abbreviation.group()
            and rule not in by_abbreviation
        ):
            reverse[rule] = name
            by_abbreviation.add(rule)
        else:
            reverse.setdefault(rule, name)
    return reverse


class TimezoneRules:
    """Name -> POSIX rule for the table's zones, read from the tz database.

    The table's rules are a snapshot of posix_tz_db. The tz database Home
    Assistant itself depends on (the ``tzdata`` package, or the system copy)
    is updated with every release and already disagrees with that snapshot
    for several zones (Alberta and British Columbia dropped DST in 2026), so
    a name's rule comes from its TZif footer whenever one can be read and the
    table only fills in for names the database lacks. Reading the display
    map from the same source keeps a stored rule reading back as the zone
    that was set.

    ``diverging`` holds the zones whose footer rule gets the clock wrong on
    some date from now on (see _first_divergence), as ``(rule, date)``. They
    are refused with that spelled out, and kept out of the display map so
    that a rule pasted regardless shows as the rule it is.
    """

    def __init__(self, rules: dict[str, str], diverging: dict[str, tuple[str, str]]) -> None:
        self.rules = rules
        self.diverging = diverging
        self._lower = {name.lower(): name for name in rules}
        self._lower_diverging = {name.lower(): name for name in diverging}
        self._by_rule = _build_rule_to_name(rules)

    def lookup(self, value: str) -> tuple[str, str] | None:
        """``(name, rule)`` for a usable table name, matched case-insensitively."""
        name = self._lower.get(value.lower())
        return None if name is None else (name, self.rules[name])

    def lookup_diverging(self, value: str) -> tuple[str, str, str] | None:
        """``(name, rule, date)`` for a table name whose rule goes wrong on ``date``."""
        name = self._lower_diverging.get(value.lower())
        return None if name is None else (name, *self.diverging[name])

    def name_for_rule(self, rule: str, preferred: list[str | None]) -> str | None:
        """Name to display for a stored rule, or None if no zone uses it.

        ``preferred`` names (the remembered choice, HA's own zone) win when
        their rule matches; otherwise the table's first zone with that rule.
        """
        for name in preferred:
            if name and self.rules.get(name) == rule:
                return name
        return self._by_rule.get(rule)


_TABLE_RULES = TimezoneRules(dict(TIMEZONES), {})


def load_timezone_rules(now: float | None = None) -> TimezoneRules:
    """Build the rules from the tz database, table as fallback (blocking I/O)."""
    now = time.time() if now is None else now
    rules: dict[str, str] = {}
    diverging: dict[str, tuple[str, str]] = {}
    for name, table_rule in TIMEZONES.items():
        found = posix_rule_from_tzif(name, now)
        if found is None:
            rules[name] = table_rule
        elif found[1] is not None:
            diverging[name] = (found[0], found[1])
        else:
            rules[name] = found[0]
    return TimezoneRules(rules, diverging)


async def async_setup_timezone_rules(hass: HomeAssistant) -> None:
    """Load the rules once per Home Assistant session; a tzdata update comes with a restart."""
    if DATA_TIMEZONE_RULES not in hass.data:
        hass.data[DATA_TIMEZONE_RULES] = await hass.async_add_executor_job(load_timezone_rules)


def get_timezone_rules(hass: HomeAssistant) -> TimezoneRules:
    """The loaded rules, or the bare table if setup has not run."""
    rules: TimezoneRules | None = hass.data.get(DATA_TIMEZONE_RULES)
    return _TABLE_RULES if rules is None else rules


def _diverging_message(name: str, rule: str, date: str) -> str:
    return (
        f"The frame can only hold one recurring POSIX rule, and none describes {name} from "
        f"now on: the tz database's long-term rule for it, {rule}, gets the clock wrong on "
        f"{date}. Enter a POSIX TZ rule by hand instead"
    )


async def async_resolve_timezone(hass: HomeAssistant, value: str) -> tuple[str | None, str]:
    """Turn user input into ``(table_name, posix_rule)``.

    A table name (case-insensitively) resolves to its rule and comes back as
    ``table_name`` so it can be shown again. Any other IANA key is looked up
    in the tz database and comes back with ``table_name`` None, so it is
    shown canonicalised through the table ("US/Pacific" reads back as
    "America/Los_Angeles"). Anything else must itself be a plausible POSIX
    rule and is passed through. Raises ValueError with a user-facing message.
    """
    value = value.strip()
    if not value:
        raise ValueError("Time zone must not be empty")
    rules = get_timezone_rules(hass)
    if (known := rules.lookup(value)) is not None:
        return known
    if (diverging := rules.lookup_diverging(value)) is not None:
        raise ValueError(_diverging_message(*diverging))
    if _IANA_KEY_RE.match(value):
        found = await hass.async_add_executor_job(posix_rule_from_tzif, value)
        if found is not None:
            rule, diverges_on = found
            if diverges_on is not None:
                raise ValueError(_diverging_message(value, rule, diverges_on))
            return None, rule
    validate_posix_rule(value)
    return None, value


def remember_timezone_name(hass: HomeAssistant, entry: ConfigEntry, name: str | None) -> None:
    """Persist (or clear) the IANA name behind the rule now on the device."""
    if entry.options.get(OPTION_TIMEZONE_NAME, "") == (name or ""):
        return
    new_options = dict(entry.options)
    new_options[OPTION_TIMEZONE_NAME] = name or ""
    hass.config_entries.async_update_entry(entry, options=new_options)
