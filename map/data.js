// The index of every dive site's coordinates, read by map.html. A new site file
// needs an entry here too: { slug, name, region, type ("shore" or "boat"), file,
// site: { lat, lon }, parking: { lat, lon } or null, entry: { lat, lon } or null }.
// `site` is the dive site's own coordinate from the file's Coordinates row, never
// the entry or the parking. `parking` and `entry` come from the file's own Parking
// coordinates and Entry point coordinates rows; both are shore-only, null for a
// boat-only site.
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
      "name": "16. 1000 Steps",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/16-1000-steps.md",
      "site": {
        "lat": 12.210183,
        "lon": -68.322317
      },
      "entry": {
        "lat": 12.210819,
        "lon": -68.321801
      },
      "parking": {
        "lat": 12.210771,
        "lon": -68.321427
      }
    },
    {
      "slug": "35-18th-palm",
      "name": "35. 18th Palm",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/35-18th-palm.md",
      "site": {
        "lat": 12.13735,
        "lon": -68.277617
      },
      "entry": {
        "lat": 12.138323,
        "lon": -68.276306
      },
      "parking": {
        "lat": 12.139089,
        "lon": -68.275807
      }
    },
    {
      "slug": "45-alice-in-wonderland",
      "name": "45. Alice in Wonderland",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/45-alice-in-wonderland.md",
      "site": {
        "lat": 12.099233,
        "lon": -68.286217
      },
      "entry": {
        "lat": 12.099763,
        "lon": -68.285356
      },
      "parking": {
        "lat": 12.099821,
        "lon": -68.285238
      }
    },
    {
      "slug": "23-andrea-i",
      "name": "23. Andrea I",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/23-andrea-i.md",
      "site": {
        "lat": 12.189217,
        "lon": -68.297483
      },
      "entry": {
        "lat": 12.188403,
        "lon": -68.296632
      },
      "parking": {
        "lat": 12.188068,
        "lon": -68.296546
      }
    },
    {
      "slug": "22-andrea-ii",
      "name": "22. Andrea II",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/22-andrea-ii.md",
      "site": {
        "lat": 12.1916,
        "lon": -68.2986
      },
      "entry": {
        "lat": 12.191665,
        "lon": -68.297882
      },
      "parking": {
        "lat": 12.191581,
        "lon": -68.297662
      }
    },
    {
      "slug": "44-angel-city",
      "name": "44. Angel City",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/44-angel-city.md",
      "site": {
        "lat": 12.10275,
        "lon": -68.288267
      },
      "entry": {
        "lat": 12.103335,
        "lon": -68.287277
      },
      "parking": {
        "lat": 12.10338,
        "lon": -68.28722
      }
    },
    {
      "slug": "46-aquarius",
      "name": "46. Aquarius",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/46-aquarius.md",
      "site": {
        "lat": 12.098195,
        "lon": -68.285925
      },
      "entry": {
        "lat": 12.098373,
        "lon": -68.284879
      },
      "parking": {
        "lat": 12.09841,
        "lon": -68.284777
      }
    },
    {
      "slug": "57-atlantis",
      "name": "57. Atlantis",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/57-atlantis.md",
      "site": {
        "lat": 12.043843,
        "lon": -68.267795
      },
      "entry": {
        "lat": 12.044189,
        "lon": -68.266715
      },
      "parking": {
        "lat": 12.044341,
        "lon": -68.266361
      }
    },
    {
      "slug": "38-bachelors-beach",
      "name": "38. Bachelor's Beach",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/38-bachelors-beach.md",
      "site": {
        "lat": 12.125899,
        "lon": -68.288135
      },
      "entry": {
        "lat": 12.1255,
        "lon": -68.287336
      },
      "parking": {
        "lat": 12.125443,
        "lon": -68.287218
      }
    },
    {
      "slug": "30-baris-reef",
      "name": "30. Bari's Reef",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/30-baris-reef.md",
      "site": {
        "lat": 12.167345,
        "lon": -68.287797
      },
      "entry": {
        "lat": 12.167271,
        "lon": -68.287153
      },
      "parking": {
        "lat": 12.167355,
        "lon": -68.286815
      }
    },
    {
      "slug": "21-barkadera",
      "name": "21. Barkadera",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/21-barkadera.md",
      "site": {
        "lat": 12.197542,
        "lon": -68.304702
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "04-bise-morto",
      "name": "4. Bise Morto",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/04-bise-morto.md",
      "site": {
        "lat": 12.279766,
        "lon": -68.414758
      },
      "entry": {
        "lat": 12.279661,
        "lon": -68.414086
      },
      "parking": {
        "lat": 12.279677,
        "lon": -68.414
      }
    },
    {
      "slug": "12-bloodlet",
      "name": "12. Bloodlet",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/12-bloodlet.md",
      "site": {
        "lat": 12.215249,
        "lon": -68.3418
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "01-boka-bartol",
      "name": "1. Boka Bartol",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/01-boka-bartol.md",
      "site": {
        "lat": 12.304327,
        "lon": -68.398804
      },
      "entry": {
        "lat": 12.303201,
        "lon": -68.398433
      },
      "parking": {
        "lat": 12.303096,
        "lon": -68.398304
      }
    },
    {
      "slug": "06-boka-slagbaai-n",
      "name": "6. Boka Slagbaai N",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/06-boka-slagbaai-n.md",
      "site": {
        "lat": 12.265367,
        "lon": -68.41435
      },
      "entry": {
        "lat": 12.264879,
        "lon": -68.413619
      },
      "parking": {
        "lat": 12.264696,
        "lon": -68.413442
      }
    },
    {
      "slug": "06a-boka-slagbaai-s",
      "name": "6a. Boka Slagbaai S",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/06a-boka-slagbaai-s.md",
      "site": {
        "lat": 12.264696,
        "lon": -68.414429
      },
      "entry": {
        "lat": 12.264486,
        "lon": -68.413711
      },
      "parking": {
        "lat": 12.264696,
        "lon": -68.413442
      }
    },
    {
      "slug": "15-bon-bini-na-kas",
      "name": "15. Bon Bini na Kas",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/15-bon-bini-na-kas.md",
      "site": {
        "lat": 12.2122,
        "lon": -68.3306
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "g-bonaventure",
      "name": "G. Bonaventure",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/g-bonaventure.md",
      "site": {
        "lat": 12.14535,
        "lon": -68.30445
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "29-buddys-reef",
      "name": "29. Buddy's Reef",
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
      },
      "parking": {
        "lat": 12.171482,
        "lon": -68.287738
      }
    },
    {
      "slug": "63-cai",
      "name": "63. Cai",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/63-cai.md",
      "site": {
        "lat": 12.10191,
        "lon": -68.221214
      },
      "entry": {
        "lat": 12.102627,
        "lon": -68.221675
      },
      "parking": {
        "lat": 12.102942,
        "lon": -68.222018
      }
    },
    {
      "slug": "34-calabas-reef",
      "name": "34. Calabas Reef",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/34-calabas-reef.md",
      "site": {
        "lat": 12.14511,
        "lon": -68.276527
      },
      "entry": {
        "lat": 12.144905,
        "lon": -68.276419
      },
      "parking": {
        "lat": 12.145309,
        "lon": -68.276054
      }
    },
    {
      "slug": "k-capt-dons-reef",
      "name": "K. Capt. Don's Reef",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/k-capt-dons-reef.md",
      "site": {
        "lat": 12.150117,
        "lon": -68.31735
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "08-carels-vision",
      "name": "8. Carel's Vision",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/08-carels-vision.md",
      "site": {
        "lat": 12.235,
        "lon": -68.4135
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "v-carls-hill",
      "name": "V. Carl's Hill",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/v-carls-hill.md",
      "site": {
        "lat": 12.16421,
        "lon": -68.323728
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "u-ch-annex",
      "name": "U. C.H. Annex (Yellow M.)",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/u-ch-annex.md",
      "site": {
        "lat": 12.164597,
        "lon": -68.323728
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "39-chez-hines",
      "name": "39. Chez Hines",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/39-chez-hines.md",
      "site": {
        "lat": 12.1191,
        "lon": -68.293217
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "26-cliff",
      "name": "26. Cliff",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/26-cliff.md",
      "site": {
        "lat": 12.1734,
        "lon": -68.28995
      },
      "entry": {
        "lat": 12.174198,
        "lon": -68.290179
      },
      "parking": {
        "lat": 12.174476,
        "lon": -68.2899
      }
    },
    {
      "slug": "37-corporal-meiss",
      "name": "37. Corporal Meiss",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/37-corporal-meiss.md",
      "site": {
        "lat": 12.133236,
        "lon": -68.282685
      },
      "entry": {
        "lat": 12.132775,
        "lon": -68.282443
      },
      "parking": {
        "lat": 12.132565,
        "lon": -68.282272
      }
    },
    {
      "slug": "14-country-garden",
      "name": "14. Country Garden",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/14-country-garden.md",
      "site": {
        "lat": 12.213389,
        "lon": -68.3346
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "b-ebos-reef",
      "name": "B. Ebo's Reef",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/b-ebos-reef.md",
      "site": {
        "lat": 12.165383,
        "lon": -68.2964
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "w-ebos-special",
      "name": "W. Ebo's Special",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/w-ebos-special.md",
      "site": {
        "lat": 12.165783,
        "lon": -68.31925
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "n-forest",
      "name": "N. Forest",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/n-forest.md",
      "site": {
        "lat": 12.14903,
        "lon": -68.32651
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "31-front-porch",
      "name": "31. Front Porch",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/31-front-porch.md",
      "site": {
        "lat": 12.164287,
        "lon": -68.287636
      },
      "entry": {
        "lat": 12.164487,
        "lon": -68.287164
      },
      "parking": {
        "lat": 12.164754,
        "lon": -68.286692
      }
    },
    {
      "slug": "m-hands-off",
      "name": "M. Hands Off",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/m-hands-off.md",
      "site": {
        "lat": 12.1502,
        "lon": -68.323517
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "43-hilma-hooker",
      "name": "43. Hilma Hooker",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/43-hilma-hooker.md",
      "site": {
        "lat": 12.104117,
        "lon": -68.28965
      },
      "entry": {
        "lat": 12.10451,
        "lon": -68.288146
      },
      "parking": {
        "lat": 12.104568,
        "lon": -68.288071
      }
    },
    {
      "slug": "51-invisibles",
      "name": "51. Invisibles",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/51-invisibles.md",
      "site": {
        "lat": 12.07754,
        "lon": -68.28136
      },
      "entry": {
        "lat": 12.077659,
        "lon": -68.280271
      },
      "parking": {
        "lat": 12.077695,
        "lon": -68.280147
      }
    },
    {
      "slug": "48-jeannies-glory",
      "name": "48. Jeannie's Glory",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/48-jeannies-glory.md",
      "site": {
        "lat": 12.0869,
        "lon": -68.2842
      },
      "entry": {
        "lat": 12.086629,
        "lon": -68.282787
      },
      "parking": {
        "lat": 12.086665,
        "lon": -68.28254
      }
    },
    {
      "slug": "18-jeff-davis-memorial",
      "name": "18. Jeff Davis Memorial",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/18-jeff-davis-memorial.md",
      "site": {
        "lat": 12.204133,
        "lon": -68.313417
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "c-jerrys-reef",
      "name": "C. Jerry's Reef",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/c-jerrys-reef.md",
      "site": {
        "lat": 12.164683,
        "lon": -68.29505
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "j-joannes-sunchi",
      "name": "J. Joanne's Sunchi",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/j-joannes-sunchi.md",
      "site": {
        "lat": 12.149833,
        "lon": -68.314933
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "d-just-a-nice-dive",
      "name": "D. Just a Nice Dive",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/d-just-a-nice-dive.md",
      "site": {
        "lat": 12.148783,
        "lon": -68.296
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "19-kallis-reef",
      "name": "19. Kalli's Reef",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/19-kallis-reef.md",
      "site": {
        "lat": 12.201567,
        "lon": -68.31075
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "09-karpata",
      "name": "9. Karpata",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/09-karpata.md",
      "site": {
        "lat": 12.218936,
        "lon": -68.3545
      },
      "entry": {
        "lat": 12.219349,
        "lon": -68.352014
      },
      "parking": {
        "lat": 12.219548,
        "lon": -68.351902
      }
    },
    {
      "slug": "f-keepsake",
      "name": "F. Keepsake",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/f-keepsake.md",
      "site": {
        "lat": 12.146389,
        "lon": -68.298236
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "y-knife",
      "name": "Y. Knife",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/y-knife.md",
      "site": {
        "lat": 12.168667,
        "lon": -68.313183
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "10-la-danias-leap",
      "name": "10. La Dania's Leap",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/10-la-danias-leap.md",
      "site": {
        "lat": 12.2175,
        "lon": -68.3495
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "27-la-machaca",
      "name": "27. La Machaca",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/27-la-machaca.md",
      "site": {
        "lat": 12.171976,
        "lon": -68.2898
      },
      "entry": {
        "lat": 12.172321,
        "lon": -68.289111
      },
      "parking": {
        "lat": 12.172232,
        "lon": -68.288451
      }
    },
    {
      "slug": "47-larrys-lair",
      "name": "47. Larry's Lair",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/47-larrys-lair.md",
      "site": {
        "lat": 12.0906,
        "lon": -68.2846
      },
      "entry": {
        "lat": 12.090358,
        "lon": -68.283457
      },
      "parking": {
        "lat": 12.090379,
        "lon": -68.2832
      }
    },
    {
      "slug": "x-leonoras-reef",
      "name": "X. Leonora's Reef",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/x-leonoras-reef.md",
      "site": {
        "lat": 12.167333,
        "lon": -68.315417
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "40-lighthouse-point",
      "name": "40. Lighthouse Point",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/40-lighthouse-point.md",
      "site": {
        "lat": 12.11435,
        "lon": -68.295417
      },
      "entry": {
        "lat": 12.114108,
        "lon": -68.294899
      },
      "parking": {
        "lat": 12.114108,
        "lon": -68.294771
      }
    },
    {
      "slug": "55-margate-bay",
      "name": "55. Margate Bay",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/55-margate-bay.md",
      "site": {
        "lat": 12.05135,
        "lon": -68.2734
      },
      "entry": {
        "lat": 12.051555,
        "lon": -68.272149
      },
      "parking": {
        "lat": 12.051768,
        "lon": -68.271853
      }
    },
    {
      "slug": "t-mi-dushi",
      "name": "T. Mi Dushi",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/t-mi-dushi.md",
      "site": {
        "lat": 12.159917,
        "lon": -68.32585
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "h-montes-divi",
      "name": "H. Monte's Divi",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/h-montes-divi.md",
      "site": {
        "lat": 12.14565,
        "lon": -68.30855
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "p-munks-haven",
      "name": "P. Munk's Haven",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/p-munks-haven.md",
      "site": {
        "lat": 12.151583,
        "lon": -68.329883
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "e-nearest-point",
      "name": "E. Nearest Point",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/e-nearest-point.md",
      "site": {
        "lat": 12.153846,
        "lon": -68.293098
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "a-no-name-beach",
      "name": "A. No Name Beach",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/a-no-name-beach.md",
      "site": {
        "lat": 12.168717,
        "lon": -68.30515
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "07-nukove",
      "name": "7. Nukove",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/07-nukove.md",
      "site": {
        "lat": 12.240933,
        "lon": -68.413333
      },
      "entry": {
        "lat": 12.240712,
        "lon": -68.412275
      },
      "parking": {
        "lat": 12.240728,
        "lon": -68.41215
      }
    },
    {
      "slug": "20-oil-slick-leap",
      "name": "20. Oil Slick Leap",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/20-oil-slick-leap.md",
      "site": {
        "lat": 12.19995,
        "lon": -68.308633
      },
      "entry": {
        "lat": 12.200149,
        "lon": -68.308632
      },
      "parking": {
        "lat": 12.200248,
        "lon": -68.308552
      }
    },
    {
      "slug": "24-petries-pillar",
      "name": "24. Petries Pillar",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/24-petries-pillar.md",
      "site": {
        "lat": 12.186267,
        "lon": -68.297
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "53-pink-beach",
      "name": "53. Pink Beach",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/53-pink-beach.md",
      "site": {
        "lat": 12.064333,
        "lon": -68.283267
      },
      "entry": {
        "lat": 12.065934,
        "lon": -68.281692
      },
      "parking": {
        "lat": 12.065908,
        "lon": -68.281478
      }
    },
    {
      "slug": "02-playa-benge",
      "name": "2. Playa Benge",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/02-playa-benge.md",
      "site": {
        "lat": 12.29085,
        "lon": -68.413067
      },
      "entry": {
        "lat": 12.290169,
        "lon": -68.411502
      },
      "parking": {
        "lat": 12.289956,
        "lon": -68.411946
      }
    },
    {
      "slug": "03-playa-funchi",
      "name": "3. Playa Funchi",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/03-playa-funchi.md",
      "site": {
        "lat": 12.282367,
        "lon": -68.4146
      },
      "entry": {
        "lat": 12.282301,
        "lon": -68.413995
      },
      "parking": {
        "lat": 12.28234,
        "lon": -68.41377
      }
    },
    {
      "slug": "41-punt-vierkant",
      "name": "41. Punt Vierkant",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/41-punt-vierkant.md",
      "site": {
        "lat": 12.1076,
        "lon": -68.291983
      },
      "entry": {
        "lat": 12.109288,
        "lon": -68.292303
      },
      "parking": {
        "lat": 12.109645,
        "lon": -68.291885
      }
    },
    {
      "slug": "11-rappel",
      "name": "11. Rappel",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/11-rappel.md",
      "site": {
        "lat": 12.21745,
        "lon": -68.3438
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "56-red-beryl",
      "name": "56. Red Beryl",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/56-red-beryl.md",
      "site": {
        "lat": 12.04655,
        "lon": -68.268957
      },
      "entry": {
        "lat": 12.046954,
        "lon": -68.268287
      },
      "parking": {
        "lat": 12.047054,
        "lon": -68.268083
      }
    },
    {
      "slug": "60-red-slave",
      "name": "60. Red Slave",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/60-red-slave.md",
      "site": {
        "lat": 12.02555,
        "lon": -68.2518
      },
      "entry": {
        "lat": 12.026288,
        "lon": -68.251255
      },
      "parking": {
        "lat": 12.026535,
        "lon": -68.251045
      }
    },
    {
      "slug": "28-reef-scientifico",
      "name": "28. Reef Scientifico",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/28-reef-scientifico.md",
      "site": {
        "lat": 12.172176,
        "lon": -68.2898
      },
      "entry": {
        "lat": 12.172321,
        "lon": -68.289111
      },
      "parking": {
        "lat": 12.172232,
        "lon": -68.288451
      }
    },
    {
      "slug": "i-rock-pile",
      "name": "I. Rock Pile",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/i-rock-pile.md",
      "site": {
        "lat": 12.147917,
        "lon": -68.311183
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "50-salt-city",
      "name": "50. Salt City",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/50-salt-city.md",
      "site": {
        "lat": 12.07942,
        "lon": -68.28219
      },
      "entry": {
        "lat": 12.081829,
        "lon": -68.281515
      },
      "parking": {
        "lat": 12.082233,
        "lon": -68.281446
      }
    },
    {
      "slug": "49-salt-pier",
      "name": "49. Salt Pier",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/49-salt-pier.md",
      "site": {
        "lat": 12.08329,
        "lon": -68.28377
      },
      "entry": {
        "lat": 12.083413,
        "lon": -68.282025
      },
      "parking": {
        "lat": 12.083581,
        "lon": -68.281869
      }
    },
    {
      "slug": "z-sampler",
      "name": "Z. Sampler",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/z-sampler.md",
      "site": {
        "lat": 12.168817,
        "lon": -68.31005
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "r-sharons-serenity",
      "name": "R. Sharon's Serenity",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/r-sharons-serenity.md",
      "site": {
        "lat": 12.155,
        "lon": -68.329
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "25-small-wall",
      "name": "25. Small Wall",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/25-small-wall.md",
      "site": {
        "lat": 12.179567,
        "lon": -68.2938
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "32-something-special",
      "name": "32. Something Special",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/32-something-special.md",
      "site": {
        "lat": 12.160958,
        "lon": -68.284499
      },
      "entry": {
        "lat": 12.161377,
        "lon": -68.283452
      },
      "parking": {
        "lat": 12.161435,
        "lon": -68.283404
      }
    },
    {
      "slug": "l-south-bay",
      "name": "L. South Bay",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/l-south-bay.md",
      "site": {
        "lat": 12.14965,
        "lon": -68.320133
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "o-south-west-corner",
      "name": "O. South West Corner",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/o-south-west-corner.md",
      "site": {
        "lat": 12.14955,
        "lon": -68.3295
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "59-sweet-dreams",
      "name": "59. Sweet Dreams",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/59-sweet-dreams.md",
      "site": {
        "lat": 12.033425,
        "lon": -68.262645
      },
      "entry": {
        "lat": 12.034321,
        "lon": -68.261544
      },
      "parking": {
        "lat": 12.03448,
        "lon": -68.261372
      }
    },
    {
      "slug": "42-the-lake",
      "name": "42. The Lake",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/42-the-lake.md",
      "site": {
        "lat": 12.106167,
        "lon": -68.290367
      },
      "entry": {
        "lat": 12.107075,
        "lon": -68.290184
      },
      "parking": {
        "lat": 12.107206,
        "lon": -68.290066
      }
    },
    {
      "slug": "13-tolo",
      "name": "13. Tolo (Ol' Blue)",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/13-tolo.md",
      "site": {
        "lat": 12.2145,
        "lon": -68.339
      },
      "entry": {
        "lat": 12.215317,
        "lon": -68.33752
      },
      "parking": {
        "lat": 12.215411,
        "lon": -68.337364
      }
    },
    {
      "slug": "52-toris-reef",
      "name": "52. Tori's Reef",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/52-toris-reef.md",
      "site": {
        "lat": 12.07115,
        "lon": -68.281667
      },
      "entry": {
        "lat": 12.070587,
        "lon": -68.280512
      },
      "parking": {
        "lat": 12.07054,
        "lon": -68.28033
      }
    },
    {
      "slug": "33-town-pier",
      "name": "33. Town Pier",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/33-town-pier.md",
      "site": {
        "lat": 12.151047,
        "lon": -68.278587
      },
      "entry": {
        "lat": 12.150107,
        "lon": -68.278066
      },
      "parking": {
        "lat": 12.150259,
        "lon": -68.277208
      }
    },
    {
      "slug": "q-twixt",
      "name": "Q. Twixt",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/q-twixt.md",
      "site": {
        "lat": 12.153521,
        "lon": -68.32965
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "s-valeries-hill",
      "name": "S. Vallerie's Hill",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/s-valeries-hill.md",
      "site": {
        "lat": 12.156999,
        "lon": -68.327
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "58-vista-blue",
      "name": "58. Vista Blue",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/58-vista-blue.md",
      "site": {
        "lat": 12.035434,
        "lon": -68.263761
      },
      "entry": {
        "lat": 12.036078,
        "lon": -68.263088
      },
      "parking": {
        "lat": 12.036246,
        "lon": -68.262836
      }
    },
    {
      "slug": "05-wayaka",
      "name": "5. Wayaka",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/05-wayaka.md",
      "site": {
        "lat": 12.26925,
        "lon": -68.414983
      },
      "entry": {
        "lat": 12.269681,
        "lon": -68.413877
      },
      "parking": {
        "lat": 12.269566,
        "lon": -68.413711
      }
    },
    {
      "slug": "17-webers-joy",
      "name": "17. Weber's Joy (Witch's Hut)",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/17-webers-joy.md",
      "site": {
        "lat": 12.2069,
        "lon": -68.3178
      },
      "entry": {
        "lat": 12.206482,
        "lon": -68.316599
      },
      "parking": {
        "lat": 12.206655,
        "lon": -68.316507
      }
    },
    {
      "slug": "62-white-hole",
      "name": "62. White Hole",
      "region": "bonaire",
      "type": "boat",
      "file": "regions/bonaire/sites/62-white-hole.md",
      "site": {
        "lat": 12.091167,
        "lon": -68.229626
      },
      "entry": null,
      "parking": null
    },
    {
      "slug": "54-white-slave",
      "name": "54. White Slave",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/54-white-slave.md",
      "site": {
        "lat": 12.055412,
        "lon": -68.2805
      },
      "entry": {
        "lat": 12.057247,
        "lon": -68.280888
      },
      "parking": {
        "lat": 12.057693,
        "lon": -68.280759
      }
    },
    {
      "slug": "61-willemstoren-lighthouse",
      "name": "61. Willemstoren Lighthouse",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/61-willemstoren-lighthouse.md",
      "site": {
        "lat": 12.026916,
        "lon": -68.236553
      },
      "entry": {
        "lat": 12.027999,
        "lon": -68.237291
      },
      "parking": {
        "lat": 12.028287,
        "lon": -68.237489
      }
    },
    {
      "slug": "36-windsock",
      "name": "36. Windsock",
      "region": "bonaire",
      "type": "shore",
      "file": "regions/bonaire/sites/36-windsock.md",
      "site": {
        "lat": 12.128741,
        "lon": -68.286613
      },
      "entry": {
        "lat": 12.130446,
        "lon": -68.284777
      },
      "parking": {
        "lat": 12.130388,
        "lon": -68.284578
      }
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
        "lat": 47.711983,
        "lon": -122.563831
      },
      "parking": {
        "lat": 47.711761,
        "lon": -122.563847
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
        "lat": 47.578369,
        "lon": -122.414576
      },
      "parking": {
        "lat": 47.578225,
        "lon": -122.413876
      }
    },
    {
      "slug": "alki-pipeline",
      "name": "Alki Pipeline",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/alki-pipeline.md",
      "site": {
        "lat": 47.569906,
        "lon": -122.41661
      },
      "entry": {
        "lat": 47.572449,
        "lon": -122.413841
      },
      "parking": {
        "lat": 47.572746,
        "lon": -122.414088
      }
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
        "lat": 48.492318,
        "lon": -122.687631
      },
      "parking": {
        "lat": 48.492507,
        "lon": -122.687545
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
        "lat": 48.12108,
        "lon": -122.490984
      },
      "parking": {
        "lat": 48.121571,
        "lon": -122.491212
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
        "lat": 47.804706,
        "lon": -122.394792
      },
      "parking": {
        "lat": 47.804724,
        "lon": -122.394138
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
        "lat": 47.813587,
        "lon": -122.382224
      },
      "parking": {
        "lat": 47.813236,
        "lon": -122.382132
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
        "lat": 48.497048,
        "lon": -122.700551
      },
      "parking": {
        "lat": 48.497994,
        "lon": -122.700806
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
        "lat": 48.091333,
        "lon": -122.692536
      },
      "parking": {
        "lat": 48.091336,
        "lon": -122.693132
      }
    },
    {
      "slug": "fort-ward",
      "name": "Fort Ward Park",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/fort-ward.md",
      "site": {
        "lat": 47.58597,
        "lon": -122.533532
      },
      "entry": {
        "lat": 47.587812,
        "lon": -122.531236
      },
      "parking": {
        "lat": 47.588358,
        "lon": -122.531159
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
      "entry": {
        "lat": 48.136278,
        "lon": -122.761603
      },
      "parking": {
        "lat": 48.136147,
        "lon": -122.762059
      }
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
        "lat": 48.497675,
        "lon": -122.70124
      },
      "parking": {
        "lat": 48.497994,
        "lon": -122.700806
      }
    },
    {
      "slug": "illahee-state-park",
      "name": "Illahee State Park",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/illahee-state-park.md",
      "site": {
        "lat": 47.600492,
        "lon": -122.593673
      },
      "entry": {
        "lat": 47.59964,
        "lon": -122.595569
      },
      "parking": {
        "lat": 47.599929,
        "lon": -122.5962
      }
    },
    {
      "slug": "illahee-town-dock",
      "name": "Illahee Town Dock",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/illahee-town-dock.md",
      "site": {
        "lat": 47.612796,
        "lon": -122.59371
      },
      "entry": {
        "lat": 47.612635,
        "lon": -122.596063
      },
      "parking": {
        "lat": 47.612655,
        "lon": -122.596508
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
        "lat": 48.136101,
        "lon": -122.36789
      },
      "parking": {
        "lat": 48.136423,
        "lon": -122.366173
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
        "lat": 48.1576,
        "lon": -122.671052
      },
      "parking": {
        "lat": 48.157895,
        "lon": -122.670765
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
      "entry": {
        "lat": 47.946514,
        "lon": -122.307873
      },
      "parking": {
        "lat": 47.946282,
        "lon": -122.307248
      }
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
        "lat": 47.949416,
        "lon": -122.302541
      },
      "parking": {
        "lat": 47.949328,
        "lon": -122.302664
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
        "lat": 47.723938,
        "lon": -122.557699
      },
      "parking": {
        "lat": 47.724294,
        "lon": -122.558222
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
      "entry": {
        "lat": 47.880524,
        "lon": -122.333531
      },
      "parking": {
        "lat": 47.880211,
        "lon": -122.332066
      }
    },
    {
      "slug": "point-white-dock",
      "name": "Point White Dock (Crystal Springs Pier)",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/point-white-dock.md",
      "site": {
        "lat": 47.599368,
        "lon": -122.577609
      },
      "entry": {
        "lat": 47.599824,
        "lon": -122.576689
      },
      "parking": {
        "lat": 47.599953,
        "lon": -122.576298
      }
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
        "lat": 47.762059,
        "lon": -122.85249
      },
      "parking": {
        "lat": 47.76199,
        "lon": -122.852503
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
        "lat": 47.763413,
        "lon": -122.385973
      },
      "parking": {
        "lat": 47.764689,
        "lon": -122.383811
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
        "lat": 47.599182,
        "lon": -122.498575
      },
      "parking": {
        "lat": 47.598768,
        "lon": -122.498591
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
        "lat": 48.417563,
        "lon": -122.6637
      },
      "parking": {
        "lat": 48.4183,
        "lon": -122.662734
      }
    },
    {
      "slug": "salt-water-state-park",
      "name": "Saltwater State Park",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/salt-water-state-park.md",
      "site": {
        "lat": 47.37287,
        "lon": -122.328268
      },
      "entry": {
        "lat": 47.372431,
        "lon": -122.324328
      },
      "parking": {
        "lat": 47.372665,
        "lon": -122.323955
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
        "lat": 47.650009,
        "lon": -122.846938
      },
      "parking": {
        "lat": 47.649207,
        "lon": -122.845768
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
        "lat": 47.588696,
        "lon": -122.379871
      },
      "parking": {
        "lat": 47.588514,
        "lon": -122.380105
      }
    },
    {
      "slug": "sund-rock-north-wall",
      "name": "Sund Rock North Wall",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/sund-rock-north-wall.md",
      "site": {
        "lat": 47.436223,
        "lon": -123.119477
      },
      "parking": {
        "lat": 47.435316,
        "lon": -123.120486
      },
      "entry": {
        "lat": 47.435722,
        "lon": -123.12026
      }
    },
    {
      "slug": "sund-rock-south-wall",
      "name": "Sund Rock South Wall",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/sund-rock-south-wall.md",
      "site": {
        "lat": 47.434256,
        "lon": -123.11959
      },
      "parking": {
        "lat": 47.435316,
        "lon": -123.120486
      },
      "entry": {
        "lat": 47.434743,
        "lon": -123.120024
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
        "lat": 47.72901,
        "lon": -122.551825
      },
      "parking": {
        "lat": 47.729221,
        "lon": -122.551809
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
        "lat": 47.452233,
        "lon": -122.379252
      },
      "parking": {
        "lat": 47.451762,
        "lon": -122.37886
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
        "lat": 48.114344,
        "lon": -122.755067
      },
      "parking": {
        "lat": 48.114982,
        "lon": -122.755759
      }
    },
    {
      "slug": "warren-avenue-bridge",
      "name": "Warren Avenue Bridge",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/warren-avenue-bridge.md",
      "site": {
        "lat": 47.578782,
        "lon": -122.632393
      },
      "entry": {
        "lat": 47.578183,
        "lon": -122.632519
      },
      "parking": {
        "lat": 47.577686,
        "lon": -122.631650
      }
    },
    {
      "slug": "port-washington-narrows",
      "name": "Port Washington Narrows",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/port-washington-narrows.md",
      "site": {
        "lat": 47.570105,
        "lon": -122.618693
      },
      "entry": {
        "lat": 47.570424,
        "lon": -122.617609
      },
      "parking": {
        "lat": 47.570440,
        "lon": -122.616692
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
        "lat": 48.141467,
        "lon": -123.430125
      },
      "parking": {
        "lat": 48.141628,
        "lon": -123.428575
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
        "lat": 48.146525,
        "lon": -123.641596
      },
      "parking": {
        "lat": 48.146296,
        "lon": -123.641655
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
        "lat": 48.142469,
        "lon": -122.782162
      },
      "parking": {
        "lat": 48.142315,
        "lon": -122.782393
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
        "lat": 48.271908,
        "lon": -124.316772
      },
      "parking": {
        "lat": 48.266619,
        "lon": -124.299257
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
        "lat": 48.323751,
        "lon": -124.469411
      },
      "parking": {
        "lat": 48.323537,
        "lon": -124.469084
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
        "lat": 48.166688,
        "lon": -123.704333
      },
      "parking": {
        "lat": 48.166488,
        "lon": -123.704596
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
        "lat": 48.266559,
        "lon": -124.298775
      },
      "parking": {
        "lat": 48.266619,
        "lon": -124.299257
      }
    },
    {
      "slug": "fay-bainbridge",
      "name": "Fay Bainbridge Park",
      "region": "puget-sound",
      "type": "shore",
      "file": "regions/puget-sound/sites/fay-bainbridge.md",
      "site": {
        "lat": 47.70333,
        "lon": -122.50332
      },
      "entry": {
        "lat": 47.70247,
        "lon": -122.506418
      },
      "parking": {
        "lat": 47.702303,
        "lon": -122.507252
      }
    },
    {
      "slug": "lake-crescent-east-beach",
      "name": "Lake Crescent East Beach",
      "region": "washington-state-lakes",
      "type": "shore",
      "file": "regions/washington-state-lakes/sites/lake-crescent-east-beach.md",
      "site": {
        "lat": 48.085275,
        "lon": -123.744945
      },
      "entry": {
        "lat": 48.085592,
        "lon": -123.743128
      },
      "parking": {
        "lat": 48.08561,
        "lon": -123.743013
      }
    }
  ]
};
