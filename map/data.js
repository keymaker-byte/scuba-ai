// The index of every dive site's coordinates, read by map.html. A new site file
// needs an entry here too: { slug, name, region, type ("shore" or "boat"), file,
// site: { lat, lon }, entry: { lat, lon } or null }. `site` is the dive site's own
// coordinate from the file's Coordinates row, never the entry point. `entry` is
// only set for a shore site whose Coordinates row gives a separate entry coordinate.
window.MAP_DATA = {
  "sites": [
    {
      "slug": "1000-steps",
      "name": "1000 Steps",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/1000-steps.md",
      "site": {
        "lat": 12.210183,
        "lon": -68.322317
      },
      "entry": {
        "lat": 12.21062,
        "lon": -68.32173
      }
    },
    {
      "slug": "18th-palm",
      "name": "18th Palm",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/18th-palm.md",
      "site": {
        "lat": 12.13735,
        "lon": -68.277617
      },
      "entry": {
        "lat": 12.137806,
        "lon": -68.276472
      }
    },
    {
      "slug": "alice-in-wonderland",
      "name": "Alice in Wonderland",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/alice-in-wonderland.md",
      "site": {
        "lat": 12.099233,
        "lon": -68.286217
      },
      "entry": null
    },
    {
      "slug": "andrea-i",
      "name": "Andrea I",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/andrea-i.md",
      "site": {
        "lat": 12.189217,
        "lon": -68.297483
      },
      "entry": {
        "lat": 12.18823,
        "lon": -68.29698
      }
    },
    {
      "slug": "andrea-ii",
      "name": "Andrea II",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/andrea-ii.md",
      "site": {
        "lat": 12.1916,
        "lon": -68.2986
      },
      "entry": {
        "lat": 12.19132,
        "lon": -68.29798
      }
    },
    {
      "slug": "angel-city",
      "name": "Angel City",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/angel-city.md",
      "site": {
        "lat": 12.10275,
        "lon": -68.288267
      },
      "entry": {
        "lat": 12.10338,
        "lon": -68.28722
      }
    },
    {
      "slug": "aquarius",
      "name": "Aquarius",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/aquarius.md",
      "site": {
        "lat": 12.094233,
        "lon": -68.284988
      },
      "entry": null
    },
    {
      "slug": "atlantis",
      "name": "Atlantis",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/atlantis.md",
      "site": {
        "lat": 12.0345,
        "lon": -68.2635
      },
      "entry": null
    },
    {
      "slug": "bachelors-beach",
      "name": "Bachelor's Beach",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/bachelors-beach.md",
      "site": {
        "lat": 12.126217,
        "lon": -68.2865
      },
      "entry": {
        "lat": 12.12553,
        "lon": -68.28732
      }
    },
    {
      "slug": "baris-reef",
      "name": "Bari's Reef",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/baris-reef.md",
      "site": {
        "lat": 12.169206,
        "lon": -68.287819
      },
      "entry": null
    },
    {
      "slug": "barkadera",
      "name": "Barkadera",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/barkadera.md",
      "site": {
        "lat": 12.197542,
        "lon": -68.304702
      },
      "entry": null
    },
    {
      "slug": "bise-morto",
      "name": "Bise Morto",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/bise-morto.md",
      "site": {
        "lat": 12.2825,
        "lon": -68.4145
      },
      "entry": null
    },
    {
      "slug": "bloodlet",
      "name": "Bloodlet",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/bloodlet.md",
      "site": {
        "lat": 12.215249,
        "lon": -68.3418
      },
      "entry": null
    },
    {
      "slug": "boka-bartol",
      "name": "Boka Bartol",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/boka-bartol.md",
      "site": {
        "lat": 12.264808,
        "lon": -68.4143
      },
      "entry": null
    },
    {
      "slug": "boka-slagbaai-n",
      "name": "Boka Slagbaai N",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/boka-slagbaai-n.md",
      "site": {
        "lat": 12.265367,
        "lon": -68.41435
      },
      "entry": {
        "lat": 12.26433,
        "lon": -68.41378
      }
    },
    {
      "slug": "boka-slagbaai-s",
      "name": "6a. Boka Slagbaai S",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/boka-slagbaai-s.md",
      "site": {
        "lat": 12.264983,
        "lon": -68.414517
      },
      "entry": {
        "lat": 12.26433,
        "lon": -68.41378
      }
    },
    {
      "slug": "bon-bini-na-kas",
      "name": "Bon Bini na Kas",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/bon-bini-na-kas.md",
      "site": {
        "lat": 12.2122,
        "lon": -68.3306
      },
      "entry": null
    },
    {
      "slug": "bonaventure",
      "name": "G. Bonaventure",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/bonaventure.md",
      "site": {
        "lat": 12.14535,
        "lon": -68.30445
      },
      "entry": null
    },
    {
      "slug": "buddys-reef",
      "name": "Buddy's Reef",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/buddys-reef.md",
      "site": {
        "lat": 12.170821,
        "lon": -68.288666
      },
      "entry": {
        "lat": 12.17075,
        "lon": -68.28843
      }
    },
    {
      "slug": "cai",
      "name": "Cai",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/cai.md",
      "site": {
        "lat": 12.10191,
        "lon": -68.221214
      },
      "entry": {
        "lat": 12.10132,
        "lon": -68.22077
      }
    },
    {
      "slug": "calabas-reef",
      "name": "Calabas Reef",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/calabas-reef.md",
      "site": {
        "lat": 12.14511,
        "lon": -68.276527
      },
      "entry": null
    },
    {
      "slug": "capt-dons-reef",
      "name": "K. Capt. Don's Reef",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/capt-dons-reef.md",
      "site": {
        "lat": 12.150117,
        "lon": -68.31735
      },
      "entry": null
    },
    {
      "slug": "carels-vision",
      "name": "Carel's Vision",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/carels-vision.md",
      "site": {
        "lat": 12.235,
        "lon": -68.4135
      },
      "entry": null
    },
    {
      "slug": "carls-hill",
      "name": "V. Carl's Hill",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/carls-hill.md",
      "site": {
        "lat": 12.16421,
        "lon": -68.323728
      },
      "entry": null
    },
    {
      "slug": "ch-annex",
      "name": "U. C.H. Annex (Yellow M.)",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/ch-annex.md",
      "site": {
        "lat": 12.164597,
        "lon": -68.323728
      },
      "entry": null
    },
    {
      "slug": "chez-hines",
      "name": "Chez Hines",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/chez-hines.md",
      "site": {
        "lat": 12.1191,
        "lon": -68.293217
      },
      "entry": null
    },
    {
      "slug": "cliff",
      "name": "Cliff",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/cliff.md",
      "site": {
        "lat": 12.1734,
        "lon": -68.28995
      },
      "entry": {
        "lat": 12.17327,
        "lon": -68.28958
      }
    },
    {
      "slug": "corporal-meiss",
      "name": "Corporal Meiss",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/corporal-meiss.md",
      "site": {
        "lat": 12.13,
        "lon": -68.286
      },
      "entry": null
    },
    {
      "slug": "country-garden",
      "name": "Country Garden",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/country-garden.md",
      "site": {
        "lat": 12.213389,
        "lon": -68.3346
      },
      "entry": null
    },
    {
      "slug": "ebos-reef",
      "name": "B. Ebo's Reef",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/ebos-reef.md",
      "site": {
        "lat": 12.165383,
        "lon": -68.2964
      },
      "entry": null
    },
    {
      "slug": "ebos-special",
      "name": "W. Ebo's Special",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/ebos-special.md",
      "site": {
        "lat": 12.165783,
        "lon": -68.31925
      },
      "entry": null
    },
    {
      "slug": "forest",
      "name": "N. Forest",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/forest.md",
      "site": {
        "lat": 12.14903,
        "lon": -68.32651
      },
      "entry": null
    },
    {
      "slug": "front-porch",
      "name": "Front Porch",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/front-porch.md",
      "site": {
        "lat": 12.161,
        "lon": -68.2855
      },
      "entry": {
        "lat": 12.16432,
        "lon": -68.28717
      }
    },
    {
      "slug": "hands-off",
      "name": "M. Hands Off",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/hands-off.md",
      "site": {
        "lat": 12.1502,
        "lon": -68.323517
      },
      "entry": null
    },
    {
      "slug": "hilma-hooker",
      "name": "Hilma Hooker",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/hilma-hooker.md",
      "site": {
        "lat": 12.104117,
        "lon": -68.28965
      },
      "entry": null
    },
    {
      "slug": "invisibles",
      "name": "Invisibles",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/invisibles.md",
      "site": {
        "lat": 12.07754,
        "lon": -68.28136
      },
      "entry": null
    },
    {
      "slug": "jeannies-glory",
      "name": "Jeannie's Glory",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/jeannies-glory.md",
      "site": {
        "lat": 12.0869,
        "lon": -68.2842
      },
      "entry": {
        "lat": 12.08665,
        "lon": -68.28265
      }
    },
    {
      "slug": "jeff-davis-memorial",
      "name": "Jeff Davis Memorial",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/jeff-davis-memorial.md",
      "site": {
        "lat": 12.204133,
        "lon": -68.313417
      },
      "entry": null
    },
    {
      "slug": "jerrys-reef",
      "name": "C. Jerry's Reef",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/jerrys-reef.md",
      "site": {
        "lat": 12.164683,
        "lon": -68.29505
      },
      "entry": null
    },
    {
      "slug": "joannes-sunchi",
      "name": "J. Joanne's Sunchi",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/joannes-sunchi.md",
      "site": {
        "lat": 12.149833,
        "lon": -68.314933
      },
      "entry": null
    },
    {
      "slug": "just-a-nice-dive",
      "name": "D. Just a Nice Dive",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/just-a-nice-dive.md",
      "site": {
        "lat": 12.148783,
        "lon": -68.296
      },
      "entry": null
    },
    {
      "slug": "kallis-reef",
      "name": "Kalli's Reef",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/kallis-reef.md",
      "site": {
        "lat": 12.201567,
        "lon": -68.31075
      },
      "entry": null
    },
    {
      "slug": "karpata",
      "name": "Karpata",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/karpata.md",
      "site": {
        "lat": 12.218936,
        "lon": -68.3545
      },
      "entry": {
        "lat": 12.2195,
        "lon": -68.352
      }
    },
    {
      "slug": "keepsake",
      "name": "F. Keepsake",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/keepsake.md",
      "site": {
        "lat": 12.146389,
        "lon": -68.298236
      },
      "entry": null
    },
    {
      "slug": "knife",
      "name": "Y. Knife",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/knife.md",
      "site": {
        "lat": 12.168667,
        "lon": -68.313183
      },
      "entry": null
    },
    {
      "slug": "la-danias-leap",
      "name": "La Dania's Leap",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/la-danias-leap.md",
      "site": {
        "lat": 12.2175,
        "lon": -68.3495
      },
      "entry": null
    },
    {
      "slug": "la-machaca",
      "name": "La Machaca",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/la-machaca.md",
      "site": {
        "lat": 12.172176,
        "lon": -68.2898
      },
      "entry": {
        "lat": 12.17222,
        "lon": -68.28962
      }
    },
    {
      "slug": "larrys-lair",
      "name": "Larry's Lair",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/larrys-lair.md",
      "site": {
        "lat": 12.0906,
        "lon": -68.2846
      },
      "entry": {
        "lat": 12.09527,
        "lon": -68.28378
      }
    },
    {
      "slug": "leonoras-reef",
      "name": "X. Leonora's Reef",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/leonoras-reef.md",
      "site": {
        "lat": 12.167333,
        "lon": -68.315417
      },
      "entry": null
    },
    {
      "slug": "lighthouse-point",
      "name": "Lighthouse Point",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/lighthouse-point.md",
      "site": {
        "lat": 12.11435,
        "lon": -68.295417
      },
      "entry": null
    },
    {
      "slug": "margate-bay",
      "name": "Margate Bay",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/margate-bay.md",
      "site": {
        "lat": 12.05135,
        "lon": -68.2734
      },
      "entry": {
        "lat": 12.05325,
        "lon": -68.27448
      }
    },
    {
      "slug": "mi-dushi",
      "name": "T. Mi Dushi",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/mi-dushi.md",
      "site": {
        "lat": 12.159917,
        "lon": -68.32585
      },
      "entry": null
    },
    {
      "slug": "montes-divi",
      "name": "H. Monte's Divi",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/montes-divi.md",
      "site": {
        "lat": 12.14565,
        "lon": -68.30855
      },
      "entry": null
    },
    {
      "slug": "munks-haven",
      "name": "P. Munk's Haven",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/munks-haven.md",
      "site": {
        "lat": 12.151583,
        "lon": -68.329883
      },
      "entry": null
    },
    {
      "slug": "nearest-point",
      "name": "E. Nearest Point",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/nearest-point.md",
      "site": {
        "lat": 12.153846,
        "lon": -68.293098
      },
      "entry": null
    },
    {
      "slug": "no-name-beach",
      "name": "A. No Name Beach",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/no-name-beach.md",
      "site": {
        "lat": 12.168717,
        "lon": -68.30515
      },
      "entry": null
    },
    {
      "slug": "nukove",
      "name": "Nukove",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/nukove.md",
      "site": {
        "lat": 12.240933,
        "lon": -68.413333
      },
      "entry": {
        "lat": 12.2409,
        "lon": -68.41243
      }
    },
    {
      "slug": "oil-slick-leap",
      "name": "Oil Slick Leap",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/oil-slick-leap.md",
      "site": {
        "lat": 12.19995,
        "lon": -68.308633
      },
      "entry": {
        "lat": 12.20015,
        "lon": -68.30857
      }
    },
    {
      "slug": "petries-pillar",
      "name": "Petries Pillar",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/petries-pillar.md",
      "site": {
        "lat": 12.186267,
        "lon": -68.297
      },
      "entry": {
        "lat": 12.18195,
        "lon": -68.29452
      }
    },
    {
      "slug": "pink-beach",
      "name": "Pink Beach",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/pink-beach.md",
      "site": {
        "lat": 12.064333,
        "lon": -68.283267
      },
      "entry": {
        "lat": 12.062973,
        "lon": -68.28185
      }
    },
    {
      "slug": "playa-benge",
      "name": "Playa Benge",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/playa-benge.md",
      "site": {
        "lat": 12.29085,
        "lon": -68.413067
      },
      "entry": {
        "lat": 12.29022,
        "lon": -68.41192
      }
    },
    {
      "slug": "playa-funchi",
      "name": "Playa Funchi",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/playa-funchi.md",
      "site": {
        "lat": 12.282367,
        "lon": -68.4146
      },
      "entry": {
        "lat": 12.28223,
        "lon": -68.41408
      }
    },
    {
      "slug": "punt-vierkant",
      "name": "Punt Vierkant",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/punt-vierkant.md",
      "site": {
        "lat": 12.1076,
        "lon": -68.291983
      },
      "entry": {
        "lat": 12.10878,
        "lon": -68.2915
      }
    },
    {
      "slug": "rappel",
      "name": "Rappel",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/rappel.md",
      "site": {
        "lat": 12.21745,
        "lon": -68.3438
      },
      "entry": null
    },
    {
      "slug": "red-beryl",
      "name": "Red Beryl",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/red-beryl.md",
      "site": {
        "lat": 12.038456,
        "lon": -68.265213
      },
      "entry": null
    },
    {
      "slug": "red-slave",
      "name": "Red Slave",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/red-slave.md",
      "site": {
        "lat": 12.02555,
        "lon": -68.2518
      },
      "entry": null
    },
    {
      "slug": "reef-scientifico",
      "name": "Reef Scientifico",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/reef-scientifico.md",
      "site": {
        "lat": 12.172176,
        "lon": -68.2898
      },
      "entry": {
        "lat": 12.17222,
        "lon": -68.28962
      }
    },
    {
      "slug": "rock-pile",
      "name": "I. Rock Pile",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/rock-pile.md",
      "site": {
        "lat": 12.147917,
        "lon": -68.311183
      },
      "entry": null
    },
    {
      "slug": "salt-city",
      "name": "Salt City",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/salt-city.md",
      "site": {
        "lat": 12.07942,
        "lon": -68.28219
      },
      "entry": {
        "lat": 12.0825,
        "lon": -68.28172
      }
    },
    {
      "slug": "salt-pier",
      "name": "Salt Pier",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/salt-pier.md",
      "site": {
        "lat": 12.08329,
        "lon": -68.28377
      },
      "entry": null
    },
    {
      "slug": "sampler",
      "name": "Z. Sampler",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/sampler.md",
      "site": {
        "lat": 12.168817,
        "lon": -68.31005
      },
      "entry": null
    },
    {
      "slug": "sharons-serenity",
      "name": "R. Sharon's Serenity",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/sharons-serenity.md",
      "site": {
        "lat": 12.155,
        "lon": -68.329
      },
      "entry": null
    },
    {
      "slug": "small-wall",
      "name": "Small Wall",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/small-wall.md",
      "site": {
        "lat": 12.179567,
        "lon": -68.2938
      },
      "entry": null
    },
    {
      "slug": "something-special",
      "name": "Something Special",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/something-special.md",
      "site": {
        "lat": 12.161,
        "lon": -68.2865
      },
      "entry": null
    },
    {
      "slug": "south-bay",
      "name": "L. South Bay",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/south-bay.md",
      "site": {
        "lat": 12.14965,
        "lon": -68.320133
      },
      "entry": null
    },
    {
      "slug": "south-west-corner",
      "name": "O. South West Corner",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/south-west-corner.md",
      "site": {
        "lat": 12.14955,
        "lon": -68.3295
      },
      "entry": null
    },
    {
      "slug": "sweet-dreams",
      "name": "Sweet Dreams",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/sweet-dreams.md",
      "site": {
        "lat": 12.030733,
        "lon": -68.2578
      },
      "entry": {
        "lat": 12.03152,
        "lon": -68.25857
      }
    },
    {
      "slug": "the-lake",
      "name": "The Lake",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/the-lake.md",
      "site": {
        "lat": 12.106167,
        "lon": -68.290367
      },
      "entry": {
        "lat": 12.10703,
        "lon": -68.29033
      }
    },
    {
      "slug": "tolo",
      "name": "Tolo (Ol' Blue)",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/tolo.md",
      "site": {
        "lat": 12.2145,
        "lon": -68.339
      },
      "entry": null
    },
    {
      "slug": "toris-reef",
      "name": "Tori's Reef",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/toris-reef.md",
      "site": {
        "lat": 12.07115,
        "lon": -68.281667
      },
      "entry": null
    },
    {
      "slug": "town-pier",
      "name": "Town Pier",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/town-pier.md",
      "site": {
        "lat": 12.151047,
        "lon": -68.278587
      },
      "entry": null
    },
    {
      "slug": "twixt",
      "name": "Q. Twixt",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/twixt.md",
      "site": {
        "lat": 12.153521,
        "lon": -68.32965
      },
      "entry": null
    },
    {
      "slug": "valeries-hill",
      "name": "S. Vallerie's Hill",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/valeries-hill.md",
      "site": {
        "lat": 12.156999,
        "lon": -68.327
      },
      "entry": null
    },
    {
      "slug": "vista-blue",
      "name": "Vista Blue",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/vista-blue.md",
      "site": {
        "lat": 12.0335,
        "lon": -68.262
      },
      "entry": null
    },
    {
      "slug": "wayaka",
      "name": "Wayaka",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/wayaka.md",
      "site": {
        "lat": 12.26925,
        "lon": -68.414983
      },
      "entry": null
    },
    {
      "slug": "webers-joy",
      "name": "Weber's Joy (Witch's Hut)",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/webers-joy.md",
      "site": {
        "lat": 12.2069,
        "lon": -68.3178
      },
      "entry": {
        "lat": 12.20645,
        "lon": -68.3165
      }
    },
    {
      "slug": "white-hole",
      "name": "White Hole",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/white-hole.md",
      "site": {
        "lat": 12.091167,
        "lon": -68.229626
      },
      "entry": null
    },
    {
      "slug": "white-slave",
      "name": "White Slave",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/white-slave.md",
      "site": {
        "lat": 12.055412,
        "lon": -68.2805
      },
      "entry": {
        "lat": 12.05757,
        "lon": -68.28083
      }
    },
    {
      "slug": "willemstoren-lighthouse",
      "name": "Willemstoren Lighthouse",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/willemstoren-lighthouse.md",
      "site": {
        "lat": 12.023682,
        "lon": -68.244389
      },
      "entry": {
        "lat": 12.02808,
        "lon": -68.23708
      }
    },
    {
      "slug": "windsock",
      "name": "Windsock",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/windsock.md",
      "site": {
        "lat": 12.133317,
        "lon": -68.282583
      },
      "entry": null
    },
    {
      "slug": "agate-pass",
      "name": "Agate Pass",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/agate-pass.md",
      "site": {
        "lat": 47.7124,
        "lon": -122.5661
      },
      "entry": {
        "lat": 47.711832,
        "lon": -122.563798
      }
    },
    {
      "slug": "alki-beach-park",
      "name": "Alki Beach Park (Junkyard)",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/alki-beach-park.md",
      "site": {
        "lat": 47.57968,
        "lon": -122.4145
      },
      "entry": {
        "lat": 47.578382,
        "lon": -122.414514
      }
    },
    {
      "slug": "alki-pipeline",
      "name": "Alki Pipeline",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/alki-pipeline.md",
      "site": {
        "lat": 47.57219,
        "lon": -122.42109
      },
      "entry": null
    },
    {
      "slug": "burrows-pass",
      "name": "Burrows Pass (Skyline Wall)",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/burrows-pass.md",
      "site": {
        "lat": 48.49042,
        "lon": -122.69148
      },
      "entry": {
        "lat": 48.492229,
        "lon": -122.687593
      }
    },
    {
      "slug": "camano-island-state-park",
      "name": "Camano Island State Park",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/camano-island-state-park.md",
      "site": {
        "lat": 48.1183,
        "lon": -122.491
      },
      "entry": {
        "lat": 48.1214,
        "lon": -122.491
      }
    },
    {
      "slug": "edmonds-marina-beach",
      "name": "Edmonds Marina Beach (Oil Dock)",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/edmonds-marina-beach.md",
      "site": {
        "lat": 47.80441,
        "lon": -122.39792
      },
      "entry": {
        "lat": 47.804704,
        "lon": -122.394844
      }
    },
    {
      "slug": "edmonds-underwater-park",
      "name": "Edmonds Underwater Park (Brackett's Landing)",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/edmonds-underwater-park.md",
      "site": {
        "lat": 47.81574,
        "lon": -122.38457
      },
      "entry": {
        "lat": 47.81392,
        "lon": -122.3824
      }
    },
    {
      "slug": "fidalgo-head",
      "name": "Fidalgo Head",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/fidalgo-head.md",
      "site": {
        "lat": 48.49216,
        "lon": -122.70335
      },
      "entry": {
        "lat": 48.497696,
        "lon": -122.701209
      }
    },
    {
      "slug": "fort-flagler-fishing-pier",
      "name": "Fort Flagler Fishing Pier",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/fort-flagler-fishing-pier.md",
      "site": {
        "lat": 48.09127,
        "lon": -122.68855
      },
      "entry": {
        "lat": 48.09133,
        "lon": -122.69265
      }
    },
    {
      "slug": "fort-worden-pier",
      "name": "Fort Worden Pier",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/fort-worden-pier.md",
      "site": {
        "lat": 48.1356,
        "lon": -122.759
      },
      "entry": null
    },
    {
      "slug": "green-point",
      "name": "Green Point",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/green-point.md",
      "site": {
        "lat": 48.49995,
        "lon": -122.70132
      },
      "entry": {
        "lat": 48.497696,
        "lon": -122.701209
      }
    },
    {
      "slug": "kayak-point",
      "name": "Kayak Point County Park",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/kayak-point.md",
      "site": {
        "lat": 48.136,
        "lon": -122.3695
      },
      "entry": {
        "lat": 48.136,
        "lon": -122.3685
      }
    },
    {
      "slug": "keystone-jetty",
      "name": "Keystone Jetty (Fort Casey)",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/keystone-jetty.md",
      "site": {
        "lat": 48.15683,
        "lon": -122.67062
      },
      "entry": {
        "lat": 48.157535,
        "lon": -122.671067
      }
    },
    {
      "slug": "mukilteo-lighthouse-park",
      "name": "Mukilteo Lighthouse Park (Clay Wall)",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/mukilteo-lighthouse-park.md",
      "site": {
        "lat": 47.9466,
        "lon": -122.3093
      },
      "entry": null
    },
    {
      "slug": "mukilteo-t-dock",
      "name": "Mukilteo T-Dock",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/mukilteo-t-dock.md",
      "site": {
        "lat": 47.95029,
        "lon": -122.30297
      },
      "entry": {
        "lat": 47.94944,
        "lon": -122.302566
      }
    },
    {
      "slug": "old-man-house-park",
      "name": "Old Man House Park",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/old-man-house-park.md",
      "site": {
        "lat": 47.7241,
        "lon": -122.554
      },
      "entry": {
        "lat": 47.723903,
        "lon": -122.557519
      }
    },
    {
      "slug": "picnic-point-park",
      "name": "Picnic Point Park",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/picnic-point-park.md",
      "site": {
        "lat": 47.88024,
        "lon": -122.33748
      },
      "entry": null
    },
    {
      "slug": "point-whitney",
      "name": "Point Whitney",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/point-whitney.md",
      "site": {
        "lat": 47.76398,
        "lon": -122.85172
      },
      "entry": {
        "lat": 47.762052,
        "lon": -122.852223
      }
    },
    {
      "slug": "richmond-beach-park",
      "name": "Richmond Beach Park (Richmond Beach Saltwater Park)",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/richmond-beach-park.md",
      "site": {
        "lat": 47.76266,
        "lon": -122.38776
      },
      "entry": {
        "lat": 47.763445,
        "lon": -122.385919
      }
    },
    {
      "slug": "rockaway-beach",
      "name": "Rockaway Beach (Norrander's Reef)",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/rockaway-beach.md",
      "site": {
        "lat": 47.5992,
        "lon": -122.49606
      },
      "entry": {
        "lat": 47.599238,
        "lon": -122.498315
      }
    },
    {
      "slug": "rosario-beach",
      "name": "Rosario Beach",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/rosario-beach.md",
      "site": {
        "lat": 48.41745,
        "lon": -122.6668
      },
      "entry": {
        "lat": 48.417293,
        "lon": -122.664069
      }
    },
    {
      "slug": "salt-water-state-park",
      "name": "Saltwater State Park",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/salt-water-state-park.md",
      "site": {
        "lat": 47.370328,
        "lon": -122.328359
      },
      "entry": {
        "lat": 47.372339,
        "lon": -122.324648
      }
    },
    {
      "slug": "scenic-beach",
      "name": "Scenic Beach",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/scenic-beach.md",
      "site": {
        "lat": 47.65104,
        "lon": -122.85048
      },
      "entry": {
        "lat": 47.65005,
        "lon": -122.846968
      }
    },
    {
      "slug": "seacrest-cove-2",
      "name": "Seacrest Cove 2",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/seacrest-cove-2.md",
      "site": {
        "lat": 47.58932,
        "lon": -122.37826
      },
      "entry": {
        "lat": 47.588669,
        "lon": -122.379838
      }
    },
    {
      "slug": "sund-rock",
      "name": "Sund Rock",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/sund-rock.md",
      "site": {
        "lat": 47.43416,
        "lon": -123.11925
      },
      "entry": {
        "lat": 47.434712,
        "lon": -123.120138
      }
    },
    {
      "slug": "suquamish-dock",
      "name": "Suquamish Dock",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/suquamish-dock.md",
      "site": {
        "lat": 47.7291,
        "lon": -122.549
      },
      "entry": {
        "lat": 47.729,
        "lon": -122.5518
      }
    },
    {
      "slug": "three-tree-point-north",
      "name": "Three Tree Point (North)",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/three-tree-point-north.md",
      "site": {
        "lat": 47.45336,
        "lon": -122.38006
      },
      "entry": {
        "lat": 47.45223,
        "lon": -122.379188
      }
    },
    {
      "slug": "union-wharf",
      "name": "Union Wharf",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/union-wharf.md",
      "site": {
        "lat": 48.11189,
        "lon": -122.75435
      },
      "entry": {
        "lat": 48.114285,
        "lon": -122.754999
      }
    },
    {
      "slug": "ediz-hook",
      "name": "Ediz Hook (Inner Harbor)",
      "region": "strait-of-juan-de-fuca",
      "type": "shore",
      "file": "regions/strait-of-juan-de-fuca/sites/ediz-hook.md",
      "site": {
        "lat": 48.140383,
        "lon": -123.430747
      },
      "entry": {
        "lat": 48.141314,
        "lon": -123.428924
      }
    },
    {
      "slug": "freshwater-bay",
      "name": "Freshwater Bay (County Park)",
      "region": "strait-of-juan-de-fuca",
      "type": "shore",
      "file": "regions/strait-of-juan-de-fuca/sites/freshwater-bay.md",
      "site": {
        "lat": 48.15111,
        "lon": -123.63571
      },
      "entry": {
        "lat": 48.14647,
        "lon": -123.64149
      }
    },
    {
      "slug": "north-beach",
      "name": "North Beach",
      "region": "strait-of-juan-de-fuca",
      "type": "shore",
      "file": "regions/strait-of-juan-de-fuca/sites/north-beach.md",
      "site": {
        "lat": 48.14529,
        "lon": -122.78255
      },
      "entry": {
        "lat": 48.1428,
        "lon": -122.78255
      }
    },
    {
      "slug": "one-mile-beach",
      "name": "One Mile Beach",
      "region": "strait-of-juan-de-fuca",
      "type": "shore",
      "file": "regions/strait-of-juan-de-fuca/sites/one-mile-beach.md",
      "site": {
        "lat": 48.27378,
        "lon": -124.31724
      },
      "entry": {
        "lat": 48.271936,
        "lon": -124.316764
      }
    },
    {
      "slug": "pinnacle-rock",
      "name": "Pinnacle Rock",
      "region": "strait-of-juan-de-fuca",
      "type": "shore",
      "file": "regions/strait-of-juan-de-fuca/sites/pinnacle-rock.md",
      "site": {
        "lat": 48.32717,
        "lon": -124.46778
      },
      "entry": {
        "lat": 48.323794,
        "lon": -124.469359
      }
    },
    {
      "slug": "salt-creek",
      "name": "Salt Creek (Tongue Point)",
      "region": "strait-of-juan-de-fuca",
      "type": "shore",
      "file": "regions/strait-of-juan-de-fuca/sites/salt-creek.md",
      "site": {
        "lat": 48.1695,
        "lon": -123.706
      },
      "entry": {
        "lat": 48.166947,
        "lon": -123.704313
      }
    },
    {
      "slug": "sekiu",
      "name": "Sekiu Jetty",
      "region": "strait-of-juan-de-fuca",
      "type": "shore",
      "file": "regions/strait-of-juan-de-fuca/sites/sekiu.md",
      "site": {
        "lat": 48.26852,
        "lon": -124.29716
      },
      "entry": {
        "lat": 48.2666,
        "lon": -124.2985
      }
    },
    {
      "slug": "lake-crescent",
      "name": "Lake Crescent",
      "region": "washington-state-lakes",
      "type": "shore",
      "file": "regions/washington-state-lakes/sites/lake-crescent.md",
      "site": {
        "lat": 48.085275,
        "lon": -123.744945
      },
      "entry": null
    }
  ]
};
