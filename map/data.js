// The index of every dive site's coordinates, read by map.html. A new site file
// needs an entry here too: { slug, name, region, type ("shore" or "boat"), file,
// site: { lat, lon }, entry: { lat, lon } or null }. `site` is the dive site's own
// coordinate from the file's Coordinates row, never the entry point. `entry` is
// only set for a shore site whose Coordinates row gives a separate entry coordinate.
// A site's `region` is only a lookup key into `regions` below, never a path or a
// label to derive from; a new region folder needs an entry here too, keyed by its
// folder slug, giving its display name and the full path to its own steering file.
window.MAP_DATA = {
  "regions": {
    "bonaire": {
      "name": "Bonaire",
      "file": "regions/bonaire/bonaire.md"
    },
    "puget-sound": {
      "name": "Puget Sound",
      "file": "regions/puget-sound/puget-sound.md"
    },
    "strait-of-juan-de-fuca": {
      "name": "Strait of Juan de Fuca",
      "file": "regions/strait-of-juan-de-fuca/strait-of-juan-de-fuca.md"
    },
    "washington-state-lakes": {
      "name": "Washington State Lakes",
      "file": "regions/washington-state-lakes/washington-state-lakes.md"
    }
  },
  "sites": [
    {
      "slug": "16-1000-steps",
      "name": "1000 Steps",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/16-1000-steps.md",
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
      "slug": "35-18th-palm",
      "name": "18th Palm",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/35-18th-palm.md",
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
      "slug": "45-alice-in-wonderland",
      "name": "Alice in Wonderland",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/45-alice-in-wonderland.md",
      "site": {
        "lat": 12.099233,
        "lon": -68.286217
      },
      "entry": null
    },
    {
      "slug": "23-andrea-i",
      "name": "Andrea I",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/23-andrea-i.md",
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
      "slug": "22-andrea-ii",
      "name": "Andrea II",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/22-andrea-ii.md",
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
      "slug": "44-angel-city",
      "name": "Angel City",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/44-angel-city.md",
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
      "slug": "46-aquarius",
      "name": "Aquarius",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/46-aquarius.md",
      "site": {
        "lat": 12.094233,
        "lon": -68.284988
      },
      "entry": null
    },
    {
      "slug": "57-atlantis",
      "name": "Atlantis",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/57-atlantis.md",
      "site": {
        "lat": 12.0345,
        "lon": -68.2635
      },
      "entry": null
    },
    {
      "slug": "38-bachelors-beach",
      "name": "Bachelor's Beach",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/38-bachelors-beach.md",
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
      "slug": "30-baris-reef",
      "name": "Bari's Reef",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/30-baris-reef.md",
      "site": {
        "lat": 12.169206,
        "lon": -68.287819
      },
      "entry": null
    },
    {
      "slug": "21-barkadera",
      "name": "Barkadera",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/21-barkadera.md",
      "site": {
        "lat": 12.197542,
        "lon": -68.304702
      },
      "entry": null
    },
    {
      "slug": "04-bise-morto",
      "name": "Bise Morto",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/04-bise-morto.md",
      "site": {
        "lat": 12.2825,
        "lon": -68.4145
      },
      "entry": null
    },
    {
      "slug": "12-bloodlet",
      "name": "Bloodlet",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/12-bloodlet.md",
      "site": {
        "lat": 12.215249,
        "lon": -68.3418
      },
      "entry": null
    },
    {
      "slug": "01-boka-bartol",
      "name": "Boka Bartol",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/01-boka-bartol.md",
      "site": {
        "lat": 12.264808,
        "lon": -68.4143
      },
      "entry": null
    },
    {
      "slug": "06-boka-slagbaai-n",
      "name": "Boka Slagbaai N",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/06-boka-slagbaai-n.md",
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
      "slug": "06a-boka-slagbaai-s",
      "name": "Boka Slagbaai S",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/06a-boka-slagbaai-s.md",
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
      "slug": "15-bon-bini-na-kas",
      "name": "Bon Bini na Kas",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/15-bon-bini-na-kas.md",
      "site": {
        "lat": 12.2122,
        "lon": -68.3306
      },
      "entry": null
    },
    {
      "slug": "g-bonaventure",
      "name": "Bonaventure",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/g-bonaventure.md",
      "site": {
        "lat": 12.14535,
        "lon": -68.30445
      },
      "entry": null
    },
    {
      "slug": "29-buddys-reef",
      "name": "Buddy's Reef",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/29-buddys-reef.md",
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
      "slug": "63-cai",
      "name": "Cai",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/63-cai.md",
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
      "slug": "34-calabas-reef",
      "name": "Calabas Reef",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/34-calabas-reef.md",
      "site": {
        "lat": 12.14511,
        "lon": -68.276527
      },
      "entry": null
    },
    {
      "slug": "k-capt-dons-reef",
      "name": "Capt. Don's Reef",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/k-capt-dons-reef.md",
      "site": {
        "lat": 12.150117,
        "lon": -68.31735
      },
      "entry": null
    },
    {
      "slug": "08-carels-vision",
      "name": "Carel's Vision",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/08-carels-vision.md",
      "site": {
        "lat": 12.235,
        "lon": -68.4135
      },
      "entry": null
    },
    {
      "slug": "v-carls-hill",
      "name": "Carl's Hill",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/v-carls-hill.md",
      "site": {
        "lat": 12.16421,
        "lon": -68.323728
      },
      "entry": null
    },
    {
      "slug": "u-ch-annex",
      "name": "C.H. Annex (Yellow M.)",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/u-ch-annex.md",
      "site": {
        "lat": 12.164597,
        "lon": -68.323728
      },
      "entry": null
    },
    {
      "slug": "39-chez-hines",
      "name": "Chez Hines",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/39-chez-hines.md",
      "site": {
        "lat": 12.1191,
        "lon": -68.293217
      },
      "entry": null
    },
    {
      "slug": "26-cliff",
      "name": "Cliff",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/26-cliff.md",
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
      "slug": "37-corporal-meiss",
      "name": "Corporal Meiss",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/37-corporal-meiss.md",
      "site": {
        "lat": 12.13,
        "lon": -68.286
      },
      "entry": null
    },
    {
      "slug": "14-country-garden",
      "name": "Country Garden",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/14-country-garden.md",
      "site": {
        "lat": 12.213389,
        "lon": -68.3346
      },
      "entry": null
    },
    {
      "slug": "b-ebos-reef",
      "name": "Ebo's Reef",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/b-ebos-reef.md",
      "site": {
        "lat": 12.165383,
        "lon": -68.2964
      },
      "entry": null
    },
    {
      "slug": "w-ebos-special",
      "name": "Ebo's Special",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/w-ebos-special.md",
      "site": {
        "lat": 12.165783,
        "lon": -68.31925
      },
      "entry": null
    },
    {
      "slug": "n-forest",
      "name": "Forest",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/n-forest.md",
      "site": {
        "lat": 12.14903,
        "lon": -68.32651
      },
      "entry": null
    },
    {
      "slug": "31-front-porch",
      "name": "Front Porch",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/31-front-porch.md",
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
      "slug": "m-hands-off",
      "name": "Hands Off",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/m-hands-off.md",
      "site": {
        "lat": 12.1502,
        "lon": -68.323517
      },
      "entry": null
    },
    {
      "slug": "43-hilma-hooker",
      "name": "Hilma Hooker",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/43-hilma-hooker.md",
      "site": {
        "lat": 12.104117,
        "lon": -68.28965
      },
      "entry": null
    },
    {
      "slug": "51-invisibles",
      "name": "Invisibles",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/51-invisibles.md",
      "site": {
        "lat": 12.07754,
        "lon": -68.28136
      },
      "entry": null
    },
    {
      "slug": "48-jeannies-glory",
      "name": "Jeannie's Glory",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/48-jeannies-glory.md",
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
      "slug": "18-jeff-davis-memorial",
      "name": "Jeff Davis Memorial",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/18-jeff-davis-memorial.md",
      "site": {
        "lat": 12.204133,
        "lon": -68.313417
      },
      "entry": null
    },
    {
      "slug": "c-jerrys-reef",
      "name": "Jerry's Reef",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/c-jerrys-reef.md",
      "site": {
        "lat": 12.164683,
        "lon": -68.29505
      },
      "entry": null
    },
    {
      "slug": "j-joannes-sunchi",
      "name": "Joanne's Sunchi",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/j-joannes-sunchi.md",
      "site": {
        "lat": 12.149833,
        "lon": -68.314933
      },
      "entry": null
    },
    {
      "slug": "d-just-a-nice-dive",
      "name": "Just a Nice Dive",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/d-just-a-nice-dive.md",
      "site": {
        "lat": 12.148783,
        "lon": -68.296
      },
      "entry": null
    },
    {
      "slug": "19-kallis-reef",
      "name": "Kalli's Reef",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/19-kallis-reef.md",
      "site": {
        "lat": 12.201567,
        "lon": -68.31075
      },
      "entry": null
    },
    {
      "slug": "09-karpata",
      "name": "Karpata",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/09-karpata.md",
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
      "slug": "f-keepsake",
      "name": "Keepsake",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/f-keepsake.md",
      "site": {
        "lat": 12.146389,
        "lon": -68.298236
      },
      "entry": null
    },
    {
      "slug": "y-knife",
      "name": "Knife",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/y-knife.md",
      "site": {
        "lat": 12.168667,
        "lon": -68.313183
      },
      "entry": null
    },
    {
      "slug": "10-la-danias-leap",
      "name": "La Dania's Leap",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/10-la-danias-leap.md",
      "site": {
        "lat": 12.2175,
        "lon": -68.3495
      },
      "entry": null
    },
    {
      "slug": "27-la-machaca",
      "name": "La Machaca",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/27-la-machaca.md",
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
      "slug": "47-larrys-lair",
      "name": "Larry's Lair",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/47-larrys-lair.md",
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
      "slug": "x-leonoras-reef",
      "name": "Leonora's Reef",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/x-leonoras-reef.md",
      "site": {
        "lat": 12.167333,
        "lon": -68.315417
      },
      "entry": null
    },
    {
      "slug": "40-lighthouse-point",
      "name": "Lighthouse Point",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/40-lighthouse-point.md",
      "site": {
        "lat": 12.11435,
        "lon": -68.295417
      },
      "entry": null
    },
    {
      "slug": "55-margate-bay",
      "name": "Margate Bay",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/55-margate-bay.md",
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
      "slug": "t-mi-dushi",
      "name": "Mi Dushi",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/t-mi-dushi.md",
      "site": {
        "lat": 12.159917,
        "lon": -68.32585
      },
      "entry": null
    },
    {
      "slug": "h-montes-divi",
      "name": "Monte's Divi",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/h-montes-divi.md",
      "site": {
        "lat": 12.14565,
        "lon": -68.30855
      },
      "entry": null
    },
    {
      "slug": "p-munks-haven",
      "name": "Munk's Haven",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/p-munks-haven.md",
      "site": {
        "lat": 12.151583,
        "lon": -68.329883
      },
      "entry": null
    },
    {
      "slug": "e-nearest-point",
      "name": "Nearest Point",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/e-nearest-point.md",
      "site": {
        "lat": 12.153846,
        "lon": -68.293098
      },
      "entry": null
    },
    {
      "slug": "a-no-name-beach",
      "name": "No Name Beach",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/a-no-name-beach.md",
      "site": {
        "lat": 12.168717,
        "lon": -68.30515
      },
      "entry": null
    },
    {
      "slug": "07-nukove",
      "name": "Nukove",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/07-nukove.md",
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
      "slug": "20-oil-slick-leap",
      "name": "Oil Slick Leap",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/20-oil-slick-leap.md",
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
      "slug": "24-petries-pillar",
      "name": "Petries Pillar",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/24-petries-pillar.md",
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
      "slug": "53-pink-beach",
      "name": "Pink Beach",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/53-pink-beach.md",
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
      "slug": "02-playa-benge",
      "name": "Playa Benge",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/02-playa-benge.md",
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
      "slug": "03-playa-funchi",
      "name": "Playa Funchi",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/03-playa-funchi.md",
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
      "slug": "41-punt-vierkant",
      "name": "Punt Vierkant",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/41-punt-vierkant.md",
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
      "slug": "11-rappel",
      "name": "Rappel",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/11-rappel.md",
      "site": {
        "lat": 12.21745,
        "lon": -68.3438
      },
      "entry": null
    },
    {
      "slug": "56-red-beryl",
      "name": "Red Beryl",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/56-red-beryl.md",
      "site": {
        "lat": 12.038456,
        "lon": -68.265213
      },
      "entry": null
    },
    {
      "slug": "60-red-slave",
      "name": "Red Slave",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/60-red-slave.md",
      "site": {
        "lat": 12.02555,
        "lon": -68.2518
      },
      "entry": null
    },
    {
      "slug": "28-reef-scientifico",
      "name": "Reef Scientifico",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/28-reef-scientifico.md",
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
      "slug": "i-rock-pile",
      "name": "Rock Pile",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/i-rock-pile.md",
      "site": {
        "lat": 12.147917,
        "lon": -68.311183
      },
      "entry": null
    },
    {
      "slug": "50-salt-city",
      "name": "Salt City",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/50-salt-city.md",
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
      "slug": "49-salt-pier",
      "name": "Salt Pier",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/49-salt-pier.md",
      "site": {
        "lat": 12.08329,
        "lon": -68.28377
      },
      "entry": null
    },
    {
      "slug": "z-sampler",
      "name": "Sampler",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/z-sampler.md",
      "site": {
        "lat": 12.168817,
        "lon": -68.31005
      },
      "entry": null
    },
    {
      "slug": "r-sharons-serenity",
      "name": "Sharon's Serenity",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/r-sharons-serenity.md",
      "site": {
        "lat": 12.155,
        "lon": -68.329
      },
      "entry": null
    },
    {
      "slug": "25-small-wall",
      "name": "Small Wall",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/25-small-wall.md",
      "site": {
        "lat": 12.179567,
        "lon": -68.2938
      },
      "entry": null
    },
    {
      "slug": "32-something-special",
      "name": "Something Special",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/32-something-special.md",
      "site": {
        "lat": 12.161,
        "lon": -68.2865
      },
      "entry": null
    },
    {
      "slug": "l-south-bay",
      "name": "South Bay",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/l-south-bay.md",
      "site": {
        "lat": 12.14965,
        "lon": -68.320133
      },
      "entry": null
    },
    {
      "slug": "o-south-west-corner",
      "name": "South West Corner",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/o-south-west-corner.md",
      "site": {
        "lat": 12.14955,
        "lon": -68.3295
      },
      "entry": null
    },
    {
      "slug": "59-sweet-dreams",
      "name": "Sweet Dreams",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/59-sweet-dreams.md",
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
      "slug": "42-the-lake",
      "name": "The Lake",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/42-the-lake.md",
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
      "slug": "13-tolo",
      "name": "Tolo (Ol' Blue)",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/13-tolo.md",
      "site": {
        "lat": 12.2145,
        "lon": -68.339
      },
      "entry": null
    },
    {
      "slug": "52-toris-reef",
      "name": "Tori's Reef",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/52-toris-reef.md",
      "site": {
        "lat": 12.07115,
        "lon": -68.281667
      },
      "entry": null
    },
    {
      "slug": "33-town-pier",
      "name": "Town Pier",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/33-town-pier.md",
      "site": {
        "lat": 12.151047,
        "lon": -68.278587
      },
      "entry": null
    },
    {
      "slug": "q-twixt",
      "name": "Twixt",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/q-twixt.md",
      "site": {
        "lat": 12.153521,
        "lon": -68.32965
      },
      "entry": null
    },
    {
      "slug": "s-valeries-hill",
      "name": "Vallerie's Hill",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/s-valeries-hill.md",
      "site": {
        "lat": 12.156999,
        "lon": -68.327
      },
      "entry": null
    },
    {
      "slug": "58-vista-blue",
      "name": "Vista Blue",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/58-vista-blue.md",
      "site": {
        "lat": 12.0335,
        "lon": -68.262
      },
      "entry": null
    },
    {
      "slug": "05-wayaka",
      "name": "Wayaka",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/05-wayaka.md",
      "site": {
        "lat": 12.26925,
        "lon": -68.414983
      },
      "entry": null
    },
    {
      "slug": "17-webers-joy",
      "name": "Weber's Joy (Witch's Hut)",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/17-webers-joy.md",
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
      "slug": "62-white-hole",
      "name": "White Hole",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/62-white-hole.md",
      "site": {
        "lat": 12.091167,
        "lon": -68.229626
      },
      "entry": null
    },
    {
      "slug": "54-white-slave",
      "name": "White Slave",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/54-white-slave.md",
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
      "slug": "61-willemstoren-lighthouse",
      "name": "Willemstoren Lighthouse",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/61-willemstoren-lighthouse.md",
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
      "slug": "36-windsock",
      "name": "Windsock",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/36-windsock.md",
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
