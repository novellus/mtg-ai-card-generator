import argparse
import copy
import difflib
import json
import itertools
import pprint
import re
import sys
import titlecase

from collections import defaultdict
from collections import namedtuple


# internally formatted cards have the following fields. Fields are always present except those indicated as optional
# {
#     'a_side'          : internal format, optional, links to parent, present only on b-, c-, d-, and e- side cards
#     'b_side'          : internal format, optional, present only on a-side (top-level) cards
#     'c_side'          : internal format, optional, present only on a-side (top-level) cards
#     'cost'            : str or None
#     'd_side'          : internal format, optional, present only on a-side (top-level) cards
#     'e_side'          : internal format, optional, present only on a-side (top-level) cards
#     'flavor'          : str or None
#     'loyalty'         : str or None
#     'main_text'       : str or None
#     'type'            : str
#     'name'            : str
#     'power_toughness' : 2-list of str or None
#     'rarity'          : str
# }


def extend_all_cases(l):
    # extends a list l with all reasonable cases for its original contents
    new = []
    new.extend([titlecase.titlecase(x) for x in l])
    new.extend([x.capitalize() for x in l])
    new.extend([x.upper() for x in l])
    new.extend([x.lower() for x in l])
    return list(set(new + l))


# constants describing mtg card attributes. These may need to be updated whenever new mechanics are released.

MTG_COUNTERS = ['Acorn', 'Aegis', 'Age', 'Aim', 'Arrow', 'Arrowhead', 'Awakening', 'Blaze', 'Blood', 'Bloodline', 'Book', 'Bounty', 'Bribery', 'Brick', 'Cage',
                'Carrion', 'Charge', 'Coin', 'Collection', 'Component', 'Contested', 'Corpse', 'Corruption', 'CRANK!', 'Credit', 'Croak', 'Crystal', 'Cube',
                'Currency', 'Death', 'Deathtouch ', 'Delay', 'Depletion', 'Descent', 'Despair', 'Devotion', 'Divinity', 'Doom', 'Double strike ', 'Dream', 'Echo',
                'Egg', 'Elixir', 'Ember', 'Energy', 'Enlightened', 'Eon', 'Experience', 'Eyeball', 'Eyestalk', 'Fade', 'Fate', 'Feather', 'Fetch', 'Filibuster',
                'First strike ', 'Flame', 'Flood', 'Flying', 'Foreshadow', 'Fungus', 'Fury', 'Fuse', 'Gem', 'Ghostform', 'Glyph', 'Gold', 'Growth', 'Hack',
                'Harmony', 'Hatching', 'Hatchling', 'Healing', 'Hexproof', 'Hit', 'Hone', 'Hoofprint', 'Hour', 'Hourglass', 'Hunger', 'Ice', 'Incarnation',
                'Indestructible', 'Infection', 'Ingenuity', 'Intel', 'Intervention', 'Invitation', 'Isolation', 'Javelin', 'Judgment', 'Keyword', 'Ki', 'Kick',
                'Knickknack', 'Knowledge', 'Landmark', 'Level', 'Lifelink', 'Lore', 'Loyalty', 'Luck', 'Magnet', 'Manabond', 'Manifestation', 'Mannequin',
                'Matrix', 'Menace', 'Midway', 'Mine', 'Mining', 'Mire', 'Music', 'Muster', 'Necrodermis', 'Net', 'Night', 'Omen', 'Ore', 'Page', 'Pain',
                'Palliation', 'Paralyzation', 'Pause', 'Petal', 'Petrification', 'Phylactery', 'Phyresis', 'Pin', 'Plague', 'Plot', 'Point', 'Poison', 'Polyp',
                'Pressure', 'Prey', 'Pupa', 'Quest', 'Reach', 'Ritual', 'Rope', 'Rust', 'Scream', 'Scroll', 'Shell', 'Shield', 'Shred', 'Silver', 'Sleep',
                'Sleight', 'Slime', 'Slumber', 'Soot', 'Soul', 'Spark', 'Spite',  'Spore', 'Stash', 'Storage', 'Strife', 'Study', 'Stun', 'Suspect', 'Task',
                'Theft', 'Ticket', 'Tide', 'Time', 'Tower', 'Training', 'Trample', 'Trap', 'Treasure', 'Unity', 'Valor', 'Velocity', 'Verse', 'Vigilance',
                'Vitality', 'Void', 'Vortex', 'Vow', 'Voyage', 'Wage', 'Winch', 'Wind', 'Wish',
]
MTG_COUNTERS = extend_all_cases(MTG_COUNTERS)
# now add +1/+1 etc counters, after the case expansion
# Note these all need to be fixed width for lookbehinds, so not an optimal expansion of a simple regex r'[\+\-]?\d+\/[\+\-]?\d+'
#   stop at 3 digits, probably nothing is bigger than that...
MTG_COUNTERS.extend([r'[\+\-]\d\/[\+\-]\d', r'\d\/[\+\-]\d', r'[\+\-]\d\/\d', r'\d\/\d',
                     r'[\+\-]\d\d\/[\+\-]\d\d', r'\d\d\/[\+\-]\d\d', r'[\+\-]\d\d\/\d\d', r'\d\d\/\d\d',
                     r'[\+\-]\d\d\d\/[\+\-]\d\d\d', r'\d\d\d\/[\+\-]\d\d\d', r'[\+\-]\d\d\d\/\d\d\d', r'\d\d\d\/\d\d\d',
                   ])

MTG_ABILITY_WORDS = ['Adamant', 'Addendum', 'Alliance', 'Battalion', 'Best in show', 'Bloodrush', 'Channel', 'Chroma', 'Cohort', 'Constellation', 'Converge',
                     'Council\'s dilemma', 'Coven', 'Crash Land', 'Delirium', 'Domain', 'Eminence', 'Enrage', 'Fateful hour', 'Ferocious', 'Formidable', 'Gear up',
                     'Gotcha!', 'Grandeur', 'Hellbent', 'Heroic', 'Imprint', 'Inspired', 'Join forces', 'Kinship', 'Landfall', 'Lieutenant', 'Magecraft',
                     'Metalcraft', 'Morbid', 'Pack tactics', 'Parade!', 'Parley', 'Radiance', 'Raid', 'Rally', 'Revolt', 'Spell mastery', 'Strive', 'Sweep',
                     'Tempting offer', 'Threshold', 'Underdog', 'Undergrowth', 'Will of the council',
]
MTG_ABILITY_WORDS = extend_all_cases(MTG_ABILITY_WORDS)

MTG_KEYWORD_ACTIONS = ['Abandon', 'Activate', 'Adapt', 'Amass', 'Assemble', 'Attach', 'Bolster', 'Cast', 'Clash', 'Connive', 'Convert', 'Counter', 'Create',
                       'Destroy', 'Detain', 'Discard', 'Double', 'Exchange', 'Exert', 'Exile', 'Explore', 'Fateseal', 'Fight', 'Goad', 'Investigate', 'Learn',
                       'Manifest', 'Meld', 'Mill', 'Monstrosity', 'Open an Attraction', 'Planeswalk', 'Play', 'Populate', 'Proliferate', 'Regenerate', 'Reveal',
                       'Roll to Visit Your Attractions', 'Sacrifice', 'Scry', 'Search', 'Set in Motion', 'Shuffle', 'Support', 'Surveil', 'Tap and Untap',
                       'Transform', 'Venture into the Dungeon', 'Vote',
                       'Return'
                       # discontinued keywords, which appear in some older cards
                       'Bury', 'Regenerate', 'Choose',
]
MTG_KEYWORD_ACTIONS = extend_all_cases(MTG_KEYWORD_ACTIONS)

MTG_KEYWORD_ABILITIES = ['Absorb', 'Affinity', 'Afflict', 'Afterlife', 'Aftermath', 'Amplify', 'Annihilator', 'Ascend', 'Assist', 'Aura Swap', 'Awaken',
                         'Banding', 'Battle Cry', 'Bestow', 'Blitz', 'Bloodthirst', 'Boast', 'Bushido', 'Buyback', 'Cascade', 'Casualty', 'Champion',
                         'Changeling', 'Cipher', 'Cleave', 'Companion', 'Compleated', 'Conspire', 'Convoke', 'Crew', 'Cumulative Upkeep', 'Cycling', 'Dash',
                         'Daybound and Nightbound', 'Deathtouch', 'Decayed', 'Defender', 'Delve', 'Demonstrate', 'Dethrone', 'Devoid', 'Devour', 'Disturb',
                         'Double Strike', 'Dredge', 'Echo', 'Embalm', 'Emerge', 'Enchant', 'Encore', 'Enlist', 'Entwine', 'Epic', 'Equip', 'Escalate', 'Escape',
                         'Eternalize', 'Evoke', 'Evolve', 'Exalted', 'Exploit', 'Extort', 'Fabricate', 'Fading', 'Fear', 'First Strike', 'Flanking', 'Flash',
                         'Flashback', 'Flying', 'Forecast', 'Foretell', 'Fortify', 'Frenzy', 'Fuse', 'Graft', 'Gravestorm', 'Haste', 'Haunt', 'Hexproof',
                         'Hidden Agenda', 'Hideaway', 'Horsemanship', 'Improvise', 'Indestructible', 'Infect', 'Ingest', 'Intimidate', 'Jump-Start', 'Kicker',
                         'Landwalk', 'Level Up', 'Lifelink', 'Living Metal', 'Living Weapon', 'Madness', 'Melee', 'Menace', 'Mentor', 'Miracle', 'Modular',
                         'More Than Meets the Eye', 'Morph', 'Mutate', 'Myriad', 'Ninjutsu', 'Offering', 'Outlast', 'Overload', 'Partner', 'Persist', 'Phasing',
                         'Poisonous', 'Protection', 'Prototype', 'Provoke', 'Prowess', 'Prowl', 'Rampage', 'Ravenous', 'Reach', 'Read Ahead', 'Rebound',
                         'Reconfigure', 'Recover', 'Reinforce', 'Renown', 'Replicate', 'Retrace', 'Riot', 'Ripple', 'Scavenge', 'Shadow', 'Shroud', 'Skulk',
                         'Soulbond', 'Soulshift', 'Space Sculptor', 'Spectacle', 'Splice', 'Split Second', 'Squad', 'Storm', 'Sunburst', 'Surge', 'Suspend',
                         'Totem Armor', 'Training', 'Trample', 'Transfigure', 'Transmute', 'Tribute', 'Undaunted', 'Undying', 'Unearth', 'Unleash', 'Vanishing',
                         'Vigilance', 'Visit', 'Ward', 'Wither',
                          # discontinued keywords, which appear in some older cards
                         'Banding', 'Fear', 'Intimidate', 'Shroud', 'Substance',
                         'Foresthome', 'Islandhome', 'Mountainhome', 'Plainshome', 'Swamphome',
                         'Forestwalk', 'Islandwalk', 'Mountainwalk', 'Plainswalk', 'Swampwalk',
                         'Phasing', 'Phase in', 'Phase out', 'Phased in', 'Phased out',
]
MTG_KEYWORD_ABILITIES = extend_all_cases(MTG_KEYWORD_ABILITIES)

# these are not defined in the comprehensive rules, but only on the one card they appear on
# we still need to know about them...
MTG_UNIQUE_KEYWORD_ABILITIES = ['A Thousand Souls Die Every Day', 'Aberrant Tinkering', 'Advanced Species', 'Aegis of the Emperor', 'Aim for the Cursed Amulet', 
                                'Aim for the Wyvern', 'Allure of Slaanesh', 'Animate Chains', 'Arcane Life-support', 'Architect of Deception',
                                'Armor of Shrieking Souls', 'Atomic Transmutation', 'Augment', 'Avoidance', 'Basic landcycling', 'Battle Cannon', 'Berzerker',
                                "Bigby's Hand", 'Bio-Plasmic Scream', 'Bio-plasmic Barrage', 'Blood Chalice', 'Blood Drain', 'Body Thief', 'Bribe the Guards',
                                'Bring it Down!', 'Brood Telepathy', 'Buy Information', "Calim's Breath", 'Call for Aid', 'Ceremorphosis', 'Chainsword',
                                'Chapter Master', 'Children of the Cult', 'Command Protocols', 'Command Section', 'Commander ninjutsu', 'Concealed Position',
                                'Confounding Clouds', 'Conjure', 'Conjure Elemental', 'Coruscating Flames', 'Crown of Madness', 'Crushing Teeth',
                                'Curse of the Walking Pox', 'Daemon Sword', 'Daybound', 'Death Frenzy', 'Death Ray', 'Desertwalk', 'Devastating Charge',
                                'Devour Intellect', 'Devourer of Souls', 'Devouring Monster', 'Disintegration Ray', 'Double agenda', 'Drain Life',
                                'Dynastic Advisor', 'Dynastic Codes', 'Dynastic Command Node', 'Echo of the First Murder', 'Electric Thunder', 'Elite Troops',
                                'Endless Swarm', 'Endurant', 'Enmitic Exterminator', 'Enthralling Performance', 'Eternity Gate', 'Executioner Round',
                                'Exile Cannon', 'Fabricator Claw Array', 'Fallen Warrior', 'Fast Healing', 'Feed', 'Feeder Mandibles', 'Field Reprogramming',
                                'Fierce Punch', 'Fire a Warning Shot', 'Fire of Tzeentch', 'Flash Kick', 'Flesh Flayer', 'Flesh Hooks', 'Forestcycling',
                                'Frenzied Metabolism', 'Frenzied Rampage', 'Friends', 'Gather Your Courage', 'Gathered Swarm', 'Gatling Blaster',
                                'Genomic Enhancement', 'Gift of Chaos', 'Gift of Tiamat', 'Grand Strategist', 'Grav-cannon', 'Guardian Patrols', 'Gust of Wind',
                                'Hadoken', 'Harbinger of Despair', 'Healing Tears', 'Heavy Power Hammer', 'Heavy Rock Cutter', "Hero's Reward", 'Hexproof from',
                                'Hire a Mercenary', 'Hive Mind', 'Homunculus Servant', 'Horrific Symbiosis', 'Hundred Hand Slap', 'Hunt for Heresy',
                                'Hyperfang Round', 'Hyperphase Threshers', 'Hypertoxic Miasma', 'Infesting Spores', 'Inquisition Agents', 'Intensity',
                                'Invasion Beams', 'Iron Muscle', 'Islandcycling', 'Jolly Gutpipes', 'Keen Sight', 'Kinfall', 'Landcycling', 'Landship',
                                'Leading from the Front', 'Legacy', 'Legendary landwalk', 'Lightning Kick', 'Locus of Slaanesh', 'Lord of Chaos', 'Lord of Torment',
                                'Lord of the Pyrrhian Legions', 'Loud Ruckus', 'Lure the Unwary', "Mama's Coming", 'Mantle of Inspiration',
                                'Mark of Chaos Ascendant', 'Martyrdom', 'Master Tactician', 'Master of Machines', 'Matter Absorption', 'Medicus Ministorum',
                                'Megamorph', 'Mold Earth', 'Mold Harvest', 'Molting Exoskeleton', 'Mountaincycling', 'Multi-threat Eliminator', 'Multikicker',
                                'My Will Be Done', 'Natural Recovery', 'Natural Shelter', 'Neurotraumal Rod', 'Nightbound', 'Nonbasic landwalk', 'Partner with',
                                'Phaeron', 'Phalanx Commander', 'Pheromone Trail', 'Plainscycling', 'Plasma Incinerator', 'Polymorphine', 'Praesidium Protectiva',
                                'Pray for Protection', 'Primarch of the Death Guard', 'Prince of Chaos', 'Prismatic Gallery', 'Probing Telepathy',
                                'Proclamator Hailer', 'Project Image', 'Protection Fighting Style', 'Protector', 'Psionic Adept', 'Psychic Abomination',
                                'Psychic Blades', 'Psychic Defense', 'Psychic Stimulus', 'Rage Beyond Death', 'Rapacious Hunger', 'Rapid Regeneration',
                                'Rapid-fire Battle Cannon', 'Repair Barge', 'Reverberating Summons', 'Rites of Banishment', 'Rogue Trader', 'Rolling Attack',
                                'Rosarius', 'Rot Fly', 'Ruinous Ascension', 'Run and Hide', 'Scavenge the Dead', 'Scorching Ray', 'Secrets of the Soul', 'Seek',
                                'Sell Contraband', 'Shieldwall', 'Shoryuken', 'Shrieking Gargoyles', 'Sigil of Corruption', 'Skilled Outrider', 'Skyswarm',
                                'Sleight of Hand', 'Slivercycling', 'Sonic Blaster', 'Sonic Boom', 'Sorcerous Elixir', 'Sorcerous Inspiration',
                                'Sphere of the Void Dragon', 'Spiked Retribution', 'Spinning Piledriver', 'Spore Chimney', 'Stall for Time', 'Stowage',
                                'Strategic Coordinator', 'Strike a Deal', 'Subterranean Assault', 'Summary Execution', 'Sumo Spirit', 'Suppressing Fire',
                                'Swampcycling', 'Symphony of Pain', 'Synapse Creature', 'Synaptic Disintegrator', 'Targeting Relay', 'Teamwork',
                                'Terror from the Deep', 'The Betrayer', 'The Seven-fold Chant', 'The Will of the Hive Mind', 'Threaten the Merchant',
                                'Three Autostubs', 'Titanic', 'Toxic Spores', 'Transdimensional Scout', 'Ultima Founding', 'Unearthly Power',
                                'Unquestionable Wisdom', 'Vanguard Species', 'Veil of Time', 'Vicious Mockery', 'Void Shields', 'Warp Blast', 'Warp Vortex',
                                'Weird Insight', 'Wild Shape', 'Wind Walk', 'Wizardcycling', 'Wraith Form', 'Xenos Cunning',
                                'Genestealer\'s Kiss', 'Bewitching Whispers',
]
MTG_UNIQUE_KEYWORD_ABILITIES = extend_all_cases(MTG_UNIQUE_KEYWORD_ABILITIES)

MTG_KEYWORDS = MTG_KEYWORD_ACTIONS + MTG_KEYWORD_ABILITIES + MTG_UNIQUE_KEYWORD_ABILITIES

# every word used in a type field
MTG_TYPE_WORDS = ["C'tan", 'Abian', 'Adventure', 'Advisor', 'Aetherborn', 'Ajani', 'Alara', 'Alicorn', 'Alien', 'Ally', 'Aminatou', 'Angel', 'Angrath',
                  'Antelope', 'Ape', 'Arcane', 'Archer', 'Archon', 'Arkhos', 'Arlinn', 'Art', 'Artifact', 'Artificer', 'Ashiok', 'Assassin', 'Assembly-Worker',
                  'Astartes', 'Atog','Attraction', 'Aura', 'Aurochs', 'Autobot', 'Avatar', 'Azgol', 'Azra', 'B.O.B.', 'Background', 'Baddest,', 'Badger', 'Bahamut',
                  'Barbarian', 'Bard', 'Basic', 'Basilisk', 'Basri', 'Bat', 'Bear', 'Beast', 'Beaver', 'Beeble', 'Beholder', 'Belenon', 'Berserker', 'Biggest,',
                  'Bird', 'Boar', 'Bolas', 'Bolas\'s Meditation Realm', 'Brainiac', 'Bringer', 'Brushwagg', 'Bureaucrat', 'Calix', 'Camel', 'Carrier', 'Cartouche',
                  'Cat', 'Centaur', 'Cephalid', 'Chameleon', 'Chandra', 'Chicken', 'Child', 'Chimera', 'Citizen', 'Clamfolk', 'Class', 'Cleric', 'Cloud', 'Clown',
                  'Clue', 'Cockatrice', 'Comet', 'Conspiracy', 'Construct', 'Contraption', 'Cow', 'Coward', 'Crab', 'Creature', 'Crocodile', 'Curse', 'Custodes',
                  'Cyborg', 'Cyclops', 'Dack', 'Dakkon', 'Daretti', 'Dauthi', 'Davriel', 'Deer', 'Demigod', 'Demon', 'Desert', 'Designer', 'Devil', 'Dihada',
                  'Dinosaur', 'Djinn', 'Dog', 'Dominaria', 'Domri', 'Donkey', 'Dovin', 'Dragon', 'Drake', 'Dreadnought', 'Drone', 'Druid', 'Dryad', 'Duck',
                  'Dungeon', 'Dwarf', 'Eaturecray', 'Efreet', 'Egg', 'Elder', 'Eldrazi', 'Elemental', 'Elemental?', 'Elephant', 'Elf', 'Elk', 'Ellywick',
                  'Elminster', 'Elspeth', 'Elves', 'Employee', 'Enchantment', 'Equilor', 'Equipment', 'Ergamon', 'Estrid', 'Etiquette', 'Ever', 'Eye', 'Fabacin',
                  'Faerie', 'Ferret', 'Fire', 'Fish', 'Flagbearer', 'Food', 'Forest', 'Fortification', 'Fox', 'Fractal', 'Freyalise', 'Frog', 'Fungus', 'Gamer',
                  'Gargoyle', 'Garruk', 'Gate', 'Giant', 'Gideon', 'Gith', 'Gnoll', 'Gnome', 'Goat', 'Goblin', 'God', 'Golem', 'Gorgon', 'Grandchild', 'Gremlin',
                  'Griffin', 'Grist', 'Guest', 'Gus', 'Hag', 'Halfling', 'Harpy', 'Hatificer', 'Head', 'Hellion', 'Hero', 'Hippo', 'Hippogriff', 'Homarid',
                  'Homunculus', 'Horror', 'Horse', 'Host', 'Huatli', 'Human', 'Hydra', 'Hyena', 'Igpay', 'Illusion', 'Imp', 'Incarnation', 'Innistrad',
                  'Inquisitor', 'Insect', 'Instant', 'instant', 'Inzerva', 'Iquatana', 'Ir', 'Island', 'Jace', 'Jackal', 'Jaguar', 'Jared', 'Jaya', 'Jellyfish',
                  'Jeska', 'Juggernaut', 'Kaito', 'Kaldheim', 'Kamigawa', 'Kangaroo', 'Karn', 'Karsus', 'Kasmina', 'Kavu', 'Kaya', 'Kephalai', 'Key', 'Killbot',
                  'Kinshala', 'Kiora', 'Kirin', 'Kithkin', 'Knight', 'Knights', 'Kobold', 'Kolbahan', 'Kor', 'Koth', 'Kraken', 'Kyneth', 'Lady', 'Lair', 'Lamia',
                  'Lammasu', 'Land', 'Leech', 'Legend', 'Legendary', 'Lesson', 'Leviathan', 'Lhurgoyf', 'Licid', 'Liliana', 'Lizard', 'Lobster', 'Locus', 'Lolth',
                  'Lorwyn', 'Lukka', 'Luvion', 'Mammoth', 'Manticore', 'Master', 'Masticore', 'Mercadia', 'Mercenary', 'Merfolk', 'Metathran', 'Mime', 'Mine',
                  'Minion', 'Minotaur', 'Minsc', 'Mirrodin', 'Moag', 'Mole', 'Monger', 'Mongoose', 'Mongseng', 'Monk', 'Monkey', 'Moonfolk', 'Mordenkainen',
                  'Mountain', 'Mouse', 'Mummy', 'Muraganda', 'Mutant', 'Myr', 'Mystic', 'Naga', 'Nahiri', 'Narset', 'Nastiest,', 'Nautilus', 'Necron', 'Nephilim',
                  'New Phyrexia', 'Nightmare', 'Nightstalker', 'Niko', 'Ninja', 'Nissa', 'Nixilis', 'Noble', 'Noggle', 'Nomad', 'Nymph', 'Octopus', 'Ogre',
                  'Oko', 'Ongoing', 'Ooze', 'Orc', 'Orgg', 'Otter', 'Ouphe', 'Ox', 'Oyster', 'Pangolin', 'Paratrooper', 'Peasant', 'Pegasus', 'Penguin',
                  'Performer', 'Pest', 'Phelddagrif', 'Phenomenon', 'Phoenix', 'Phyrexia', 'Phyrexian', 'Pilot', 'Pirate', 'Plains', 'Plane', 'Planeswalker',
                  'Plant', 'Porcupine', 'Power-Plant', 'Powerstone', 'Praetor', 'Primarch', 'Processor', 'Proper', 'Pyrulea', 'Rabbit', 'Rabiah', 'Raccoon',
                  'Ral', 'Ranger', 'Rat', 'Rath', 'Ravnica', 'Rebel', 'Reflection', 'Regatha', 'Rhino', 'Rigger', 'Robot', 'Rogue', 'Rowan', 'Rune', 'Sable',
                  'Saga', 'Saheeli', 'Salamander', 'Samurai', 'Samut', 'Sarkhan', 'Satyr', 'Scarecrow', 'Scariest', 'Scheme', 'Scientist', 'Scorpion', 'Scout',
                  'See', 'Segovia', 'Serpent', 'Serra', 'Serra\'s Realm', 'Shade', 'Shadowmoor', 'Shaman', 'Shandalar', 'Shapeshifter', 'Shark', 'Sheep', 'Ship',
                  'Shrine', 'Siren', 'Sivitri', 'Skeleton', 'Slith', 'Sliver', 'Slug', 'Snake', 'Snow', 'Soldier', 'Soltari', 'Sorcery', 'Sorin', 'Spawn',
                  'Specter', 'Spellshaper', 'Sphinx', 'Spider', 'Spike', 'Spirit', 'Sponge', 'Spy', 'Squid', 'Squirrel', 'Starfish', 'Sticker', 'Summon',
                  'Surrakar', 'Swamp', 'Szat', 'Tamiyo', 'Tasha', 'Teferi', 'Teyo', 'Tezzeret', 'Thalakos', 'Thopter', 'Thrull', 'Tibalt', 'Tiefling',
                  'Tower', 'Townsfolk', 'Trap', 'Treasure', 'Treefolk', 'Tribal', 'Trilobite', 'Troll', 'Turtle', 'Tyranid', 'Tyvar', 'Ugin', 'Ulgrotha',
                  'Unicorn', 'Urza', 'Urza\'s', 'Valla', 'Vampire', 'Vampyre', 'Vanguard', 'Vedalken', 'Vehicle', 'Venser', 'Viashino', 'Villain', 'Vivien',
                  'Volver', 'Vraska', 'Vryn', 'Waiter', 'Wall', 'Walrus', 'Warlock', 'Warrior', 'Weird', 'Werewolf', 'Whale', 'Wildfire', 'Will', 'Windgrace',
                  'Wizard', 'Wolf', 'Wolverine', 'Wombat', 'World', 'Worm', 'Wraith', 'Wrenn', 'Wrestler', 'Wurm', 'Xenagos', 'Xerex', 'Yanggu', 'Yanling',
                  'Yeti', 'You\'ll', 'Zariel', 'Zendikar', 'Zombie', 'Zubera',
                  'Blinkmoth', 'Rat', 'Rats', 'Servo', 'Caribou'
]
MTG_TYPE_WORDS = extend_all_cases(MTG_TYPE_WORDS)

# mana symbols use an extensible encoding mechanism so the AI can understand mana combinations and create new ones
#   ie those similar to but technically unused in the base set {B/R/P}
#   Use original encoding with a few modifications
#       Use a leading ⓿ instead of brackets on both sides to reduce syntax burden on the AI
#       drop all slashes
#       numbered mana will be encoded in unary separately, so are not included in this list
#           except big numbers, which don't make sense in unary
#       multicharacter base symbols get a unique single character encoding
#           chaos
#           tikets
#           big numbers
#       all modifiers to the base symbol go to the right of the base symbol. This is mostly the case already, except
#           half 'H' symbol goes to the right of the base symbol, to be consistent with all other modfifiers
#           2 also goes to the right of the color (treating the color as the base symbol for an improved sampling distribution from the AI)
#       remaining letters and numbers are replaced with unique unicode characters, to avoid overloading character definitions for the AI
#           this trades lower character overloading at the AI interface for increased vocab size
#           as long as the vocab size doesn't go above 255, it doesn't have much performance impact
# this is not entirely snytax free like I wanted, but we're trading some syntax for extensibility which is a win
#   this is only slightly lower syntax than the original mtgencode library used, but more capable
#       and we traided up the number of syntax tokens ({} surrounding mana blocks vs leading character per mana) for local only syntax, which might be a win?
#   We can't quite eliminate the syntax
#       leading or trailing mana separator is necessary so that encoded 'WU' -> ('{W/U}' or '{W}{U}') is not confusing
#       a consistent leading character is probably simpler for the AI to understand than extra spaces
#           and X, Y, Z, ½, ∞ already rerquire an additional character to distinguish usage as symbols vs text
#           or they could use unique characters instead, but then the AI has less relatedness information
MTG_SYMBOL_JSON_TO_AI_FORMAT = {
    '{1000000}' : '⓿Ⓛ',    # special case, because we're not encoding that number in unary...
    '{100}'     : '⓿Ⓝ',    # special case, because we're not encoding that number in unary...
    '{2/B}'     : '⓿Ⓑ⓶',   # Monocolored hybrid mana
    '{2/G}'     : '⓿Ⓖ⓶',   # Monocolored hybrid mana
    '{2/R}'     : '⓿Ⓡ⓶',   # Monocolored hybrid mana
    '{2/U}'     : '⓿Ⓤ⓶',   # Monocolored hybrid mana
    '{2/W}'     : '⓿Ⓦ⓶',   # Monocolored hybrid mana
    '{A}'       : '⓿Ⓐ',    # Acorn counter
    '{B/G/P}'   : '⓿ⒷⒼⓅ',  # Phyrexian hybrid mana
    '{B/G}'     : '⓿ⒷⒼ',   # Hybrid mana
    '{B/P}'     : '⓿ⒷⓅ',   # Phyrexian mana
    '{B/R/P}'   : '⓿ⒷⓇⓅ',  # Phyrexian hybrid mana
    '{B/R}'     : '⓿ⒷⓇ',   # Hybrid mana
    '{B}'       : '⓿Ⓑ',    # Standard black mana
    '{CHAOS}'   : '⓿Ⓞ',    # Chaos
    '{C}'       : '⓿Ⓒ',    # Colorless only
    '{E}'       : '⓿Ⓔ',    # Energy
    '{G/P}'     : '⓿ⒼⓅ',   # Phyrexian mana
    '{G/U/P}'   : '⓿ⒼⓊⓅ',  # Phyrexian hybrid mana
    '{G/U}'     : '⓿ⒼⓊ',   # Hybrid mana
    '{G/W/P}'   : '⓿ⒼⓌⓅ',  # Phyrexian hybrid mana
    '{G/W}'     : '⓿ⒼⓌ',   # Hybrid mana
    '{G}'       : '⓿Ⓖ',    # Standard green mana
    '{HB}'      : '⓿ⒷⒽ',   # Half-black mana
    '{HG}'      : '⓿ⒼⒽ',   # Half-green mana
    '{HR}'      : '⓿ⓇⒽ',   # Half-red mana
    '{HS}'      : '⓿ⓈⒽ',   # Half-snow mana
    '{HU}'      : '⓿ⓊⒽ',   # Half-blue mana
    '{HW}'      : '⓿ⓌⒽ',   # Half-white mana
    '{P}'       : '⓿Ⓟ',    # Colorless Phyrexian mana
    '{Q}'       : '⓿ⓠ',    # Untap symbol
    '{R/G/P}'   : '⓿ⓇⒼⓅ',  # Phyrexian hybrid mana
    '{R/G}'     : '⓿ⓇⒼ',   # Hybrid mana
    '{R/P}'     : '⓿ⓇⓅ',   # Phyrexian mana
    '{R/W/P}'   : '⓿ⓇⓌⓅ',  # Phyrexian hybrid mana
    '{R/W}'     : '⓿ⓇⓌ',   # Hybrid mana
    '{R}'       : '⓿Ⓡ',    # Standard red mana
    '{S}'       : '⓿Ⓢ',    # Snow
    '{TK}'      : '⓿Ⓚ',    # Tokens
    '{T}'       : '⓿Ⓣ',    # Tap symbol
    '{U/B/P}'   : '⓿ⓊⒷⓅ',  # Phyrexian hybrid mana
    '{U/B}'     : '⓿ⓊⒷ',   # Hybrid mana
    '{U/P}'     : '⓿ⓊⓅ',   # Phyrexian mana
    '{U/R/P}'   : '⓿ⓊⓇⓅ',  # Phyrexian hybrid mana
    '{U/R}'     : '⓿ⓊⓇ',   # Hybrid mana
    '{U}'       : '⓿Ⓤ',    # Standard blue mana
    '{W/B/P}'   : '⓿ⓌⒷⓅ',  # Phyrexian hybrid mana
    '{W/B}'     : '⓿ⓌⒷ',   # Hybrid mana
    '{W/P}'     : '⓿ⓌⓅ',   # Phyrexian mana
    '{W/U/P}'   : '⓿ⓌⓊⓅ',  # Phyrexian hybrid mana
    '{W/U}'     : '⓿ⓌⓊ',   # Hybrid mana
    '{W}'       : '⓿Ⓦ',    # Standard white mana
    '{X}'       : '⓿Ⓧ',    # Variable 'X' mana
    '{Y}'       : '⓿Ⓨ',    # Variable 'Y' mana
    '{Z}'       : '⓿Ⓩ',    # Variable 'Z' mana
    '{½}'       : '⓿½',    # Half colorless mana
    '{∞}'       : '⓿∞',    # infinity mana
}
MTG_SYMBOL_AI_TO_JSON_FORMAT = {v:k for k,v in MTG_SYMBOL_JSON_TO_AI_FORMAT.items()}

MTG_RARITY_JSON_TO_AI_FORMAT = {
    'Common'     : '∫',
    'Uncommon'   : '∬',
    'Rare'       : '∭',
    'Mythic'     : '∮',
    'Special'    : '∯',
    'Basic Land' : '∰',
}
MTG_RARITY_AI_TO_JSON_FORMAT = {v:k for k,v in MTG_RARITY_JSON_TO_AI_FORMAT.items()}

# reminder text will be removed
rm = namedtuple('rm', ['preface', 'reminder'])
MTG_SYMBOL_REGEX = r'\{\d+\}|' + ('|'.join([re.escape(k) for k,v in MTG_SYMBOL_JSON_TO_AI_FORMAT.items()]))
MTG_REMINDER_TEXT = [
    rm(fr'',                                                  r"\((?:\d+ |an )?energy counters?\)"),
    rm(fr'',                                                  r"\((?:This creature|This|It|You|They) can't attack, and it can block creatures with flying\.\)"),
    rm(fr'',                                                  r"\((?:To assemble a Contraption, p|P)ut the top card of your Contraption deck face up onto 1 of your sprockets\.(?: Then repeat this process\.)?\)"),
    rm(fr'',                                                  r"\(\{2/[A-Z]\} can be paid with any 2 mana or with[^\)]*\)"),
    rm(fr'',                                                  r"\(\{[A-Z]/P\} can be paid with either \{[A-Z]\} or 2 life\.\)"),
    rm(fr'',                                                  r"\(\{[A-Z]\/[A-Z]\} can be paid with either \{[A-Z]\} or \{[A-Z]\}\.\)"),
    rm(fr'',                                                  r"\(\{C\} represents colorless mana\.\)"),
    rm(fr'',                                                  r"\(\{Q\} is the untap symbol\.\)"),
    rm(fr'',                                                  r"\(\{S\} can be paid with 1 mana from a snow source\.\)"),
    rm(fr'',                                                  r"\(\{S\} is mana from a snow source\.\)"),
    rm(fr'',                                                  r"\(A creature with defender can't attack\.\)"),
    rm(fr'',                                                  r"\(A creature with hexproof can't be the target of spells or abilities your opponents control\.\)"),
    rm(fr'',                                                  r"\(A creature with menace can't be blocked except by 2 or more creatures\.\)"),
    rm(fr'',                                                  r"\(Artifacts, legendaries, and Sagas are historic\.\)"),
    rm(fr'',                                                  r"\(Artifact, creature, enchantment, instant, land, planeswalker, sorcery, and tribal are card types\.\)"),
    rm(fr'',                                                  r"\(Damage causes loss of life\.\)"),
    rm(fr'',                                                  r"\(Damage dealt by a creature with lifelink also causes its controller to gain that much life\.\)"),
    rm(fr'',                                                  r"\(That creature returns under its owner's control\.\)"),
    rm(fr'',                                                  r"\(Equipment, Auras you control, and counters are modifications\.\)"),
    rm(fr'',                                                  r"\(A copy of a permanent spell becomes a token\.\)"),
    rm(fr'',                                                  r"\(For example[^\)]*\)"),
    rm(fr'',                                                  r"\(Target a land as you cast this. This card enters the battlefield attached to that land\.\)"),
    rm(fr'',                                                  r"\(To mill a card, put the top card of your library into your graveyard\.\)"),
    rm(fr'[Aa]dapt',                                          fr"\(If this creature has no \+1\/\+1 counters on it, put (?:a|\d+) \+1\/\+1 counters? on it\.\)"),
    rm(fr'[Aa]ffinity for \w+',                               r"\((?:This|It|You|They) spell costs \{1\} less to cast for each [\w ]+ you control\.\)"),
    rm(fr'[Aa]fflict',                                        fr"\(Whenever this creature becomes blocked, defending player loses \d+ life\.\)"),
    rm(fr'[Aa]fterlife',                                      fr"\(When this creature dies, create (?:\d+|a) 1\/1 white and black Spirit creature tokens? with flying\.\)"),
    rm(fr'[Aa]mass',                                          fr"\(Put (?:\d+|a) \+1\/\+1 counters? on an Army you control. If you don't control 1, create a 0\/0 black Zombie Army creature token first\.\)"),
    rm(fr'[Aa]mplify',                                        fr"\(As this creature enters the battlefield, put (?:\d+|a) \+1\/\+1 counters? on it for each (\w+) card you reveal in your hand\.\)"),
    rm(fr'[Aa]nnihilator',                                    r"\(Whenever this creature attacks, defending player sacrifices (?:a|\d+) permanents?\.\)"),
    rm(fr'[Aa]scend',                                         r"\(If you control 10 or more permanents, you get the city's blessing for the rest of the game\.\)"),
    rm(fr'[Aa]ssist',                                         fr"\(Another player can pay up to (?:{MTG_SYMBOL_REGEX})+ of this spell's cost\.(?: You choose the value of X\.)?\)"),
    rm(fr'[Aa]ugment',                                        fr"\((?:{MTG_SYMBOL_REGEX})+, Reveal this card from your hand: Combine it with target host. Augment only as a sorcery\.\)"),
    rm(fr'[Aa]waken',                                         fr"\(If you cast this spell for (?:{MTG_SYMBOL_REGEX})+, also put \d+ \+1\/\+1 counters on target land you control and it becomes a 0/0 Elemental creature with haste. It's still a land\.\)"),
    rm(fr'[Bb]anding',                                        fr"\(Any creatures with banding, and up to 1 without, can attack in a band. Bands are blocked as a group. If any creatures with banding (?:a player|you) controls? are blocking or being blocked by a creature, (?:you|that player) divides? that creature's combat damage, not its controller, among any of the creatures it's being blocked by or is blocking\.\)"),
    rm(fr'[Bb]asic landcycling',                              fr"\((?:{MTG_SYMBOL_REGEX})+, Discard this card: Search your library for a basic land card, reveal it, put it into your hand, then shuffle\.\)"),
    rm(fr'[Bb]attle cry',                                     r"\(Whenever this creature attacks, each other attacking creature gets \+1\/\+0 until end of turn\.\)"),
    rm(fr'[Bb]estow',                                         fr"\(If you cast this card for its bestow cost, it's an Aura spell with enchant creature. It becomes a creature again if it's not attached to a creature\.\)"),
    rm(fr'[Bb]litz',                                          fr"\(If you cast this spell for its blitz cost, it gains haste and \"When this creature dies, draw a card.\" Sacrifice it at the beginning of the next end step\.\)"),
    rm(fr'[Bb]lood token',                                    r"\(It's an artifact with \"\{1\}, \{T\}, Discard a card, Sacrifice this artifact: Draw a card\.\"\)"),
    rm(fr'[Bb]loodthirst',                                    r"\(If an opponent was dealt damage this turn, this creature enters the battlefield with (?:a|\d+) \+1\/\+1 counters? on it\.\)"),
    rm(fr'[Bb]oast',                                          fr"\(Activate only if this creature attacked this turn and only once each turn\.\)"),
    rm(fr'[Bb]olster',                                        fr"\(Choose a creature with the least toughness among creatures you control and put (?:a|\d|X) \+1/\+1 counters? on it\.\)"),
    rm(fr'[Bb]ushido',                                        r"\(Whenever this creature blocks or becomes blocked, it gets \+\d+\/\+\d+ until end of turn\.\)"),
    rm(fr'[Bb]uyback',                                        fr"\(You may (?:(?:sacrifice a land|discard \d+ cards) in addition to any other costs|pay an additional (?:{MTG_SYMBOL_REGEX})+) as you cast this spell. If you do, put this card into your hand as it resolves\.\)"),
    rm(fr'[Cc]ascade',                                        r"\(When you cast this spell, exile cards from the top of your library until you exile a nonland card that costs less. You may cast it without paying its mana cost. Put the exiled cards on the bottom of your library in a random order\.\)"),
    rm(fr'[Cc]asualty',                                       fr"\(As you cast this spell, you may sacrifice a creature with power \d+ or greater. When you do, copy this spell(?: and you may choose a new target for the copy)?\.\)"),
    rm(fr'[Cc]hampion an? \w+',                               fr"\(When this enters the battlefield, sacrifice it unless you exile another \w+ you control. When this leaves the battlefield, that card returns to the battlefield\.\)"),
    rm(fr'[Cc]hangeling',                                     r"\((?:This card|It|You) is every creature type\.\)"),
    rm(fr'[Cc]ompanion',                                      r"\(If this card is your chosen companion, you may put it into your hand from outside the game for \{3\} any time you could cast a sorcery\.\)"),
    rm(fr'[Cc]hoose a [Bb]ackground',                         r"\(You can have a Background as a second commander\.\)"),
    rm(fr'[Cc]ipher',                                         r"\(Then you may exile this spell card encoded on a creature you control. Whenever that creature deals combat damage to a player, its controller may cast a copy of the encoded card without paying its mana cost\.\)"),
    rm(fr'[Cc]leave',                                         r"\(You may cast this spell for its cleave cost. If you do, remove the words in square brackets\.\)"),
    rm(fr'[Cc]lash',                                          r"\(Each clashing player reveals the top card of their library, then puts that card on the top or bottom. A player wins if their card had a higher mana value\.\)"),
    rm(fr'[Cc]onnive',                                        r"\(Draw a card, then discard a card. If you discarded a nonland card, put a \+1\/\+1 counter on this creature\.\)"),
    rm(fr'[Cc]onspire',                                       fr"\(As you cast this spell, you may tap 2 untapped creatures you control that share a color with it. When you do, copy it(?: and you may choose a new target for the copy)?\.\)"),
    rm(fr'[Cc]onvoke',                                        r"\(Your creatures can help cast this spell. Each creature you tap while casting this spell pays for \{1\} or 1 mana of that creature's color\.\)"),
    rm(fr'[Cc]rew',                                           r"\(Tap any number of creatures you control with total power \d+ or more: This Vehicle becomes an artifact creature until end of turn\.\)"),
    rm(fr'[Cc]umulative upkeep',                              r"\(At the beginning of (?:its controller's|your) upkeep,(?: that player)? puts? an age counter on this permanent, then sacrifices? it unless (?:you|they) pay its upkeep cost for each age counter on it\.(?: \{\S} can be paid with 1 mana from a snow source\.)?\)"),
    rm(fr'[Cc]ycling',                                        fr"\((?:-Sacrifice a land|Pay \d+ life|(?:{MTG_SYMBOL_REGEX})+), Discard this card: Draw a card\.\)"),
    rm(fr'[Dd]ash',                                           fr"\(You may cast this spell for its dash cost. If you do, it gains haste, and it's returned from the battlefield to its owner's hand at the beginning of the next end step\.\)"),
    rm(fr'[Dd]aybound',                                       r"\(If a player casts no spells during their own turn, it becomes night next turn\.\)"),
    rm(fr'[Dd]eathtouch',                                     r"\(Any amount of damage (?:this|that|it|they|you) deals? to a creature is enough to destroy (?:that creature|it)\.\)"),
    rm(fr'[Dd]ecayed',                                        r"\((A creature with decayed|It) can't block. When it attacks, sacrifice it at end of combat\.\)"),
    rm(fr'[Dd]efender',                                       r"\((?:This creature|This|It|You|They) can't attack\.\)"),
    rm(fr'[Dd]elve',                                          r"\(Each card you exile from your graveyard while casting this spell pays for \{1\}\.\)"),
    rm(fr'[Dd]emonstrate',                                    r"\(When you cast this spell, you may copy it. If you do, choose an opponent to also copy it\.(?: Players may choose new targets for their copies\.)?\)"),
    rm(fr'[Dd]estroy target Attractio',                       r"\(It's put into its owner's junkyard\.\)"),
    rm(fr'[Dd]ethrone',                                       r"\(Whenever this creature attacks the player with the most life or tied for most life, put a \+1\/\+1 counter on it\.\)"),
    rm(fr'[Dd]evoid',                                         r"\((?:This creature|This card|It|You|They) has no color\.\)"),
    rm(fr'[Dd]evotion to (?:black|white|blue|green|red)',     fr"\(Each (?:{MTG_SYMBOL_REGEX})+ in the mana costs of permanents you control counts toward your devotion to (?:black|white|blue|green|red)\.\)"),
    rm(fr'[Dd]evour',                                         r"\(As this enters the battlefield, you may sacrifice any number of creatures. This creature enters the battlefield with(?: twice| \d+ times)? that many \+\d+\/\+\d+ counters on it\.\)"),
    rm(fr'[Dd]isturb',                                        r"\(You may cast this card from your graveyard transformed for its disturb cost\.\)"),
    rm(fr'[Dd]ouble strike',                                  r"\((?:This creature|This|It|You|They) deals both first-strike and regular combat damage\.\)"),
    rm(fr'[Dd]redge',                                         r"\(If you would draw a card, you may mill (?:a|\d+) cards? instead. If you do, return this card from your graveyard to your hand\.\)"),
    rm(fr'[Ee]cho',                                           fr"\(At the beginning of your upkeep, if this came under your control since the beginning of your last upkeep, sacrifice it unless you pay its echo cost\.\)"),
    rm(fr'[Ee]mbalm',                                         fr"\((?:{MTG_SYMBOL_REGEX})+, Exile this card from your graveyard: Create a token that's a copy of it, except it's a white Zombie [\w ]+ with no mana cost. Embalm only as a sorcery\.\)"),
    rm(fr'[Ee]merge',                                         fr"\(You may cast this spell by sacrificing a creature and paying the emerge cost reduced by that creature's mana value\.\)"),
    rm(fr'[Ee]nchant creature',                               r"\(Target a creature as you cast this. This card enters the battlefield attached to that creature\.\)"),
    rm(fr'[Ee]ncore',                                         fr"\((?:{MTG_SYMBOL_REGEX})+, Exile this card from your graveyard: For each opponent, create a token copy that attacks that opponent this turn if able. They gain haste. Sacrifice them at the beginning of the next end step. Activate only as a sorcery\.\)"),
    rm(fr'[Ee]nd the turn',                                   r"\(Exile all spells and abilities from the stack, including this card. The player whose turn it is discards down to their maximum hand size. Damage wears off, and \"this turn\" and \"until end of turn\" effects end\.\)"),
    rm(fr'[Ee]nd the turn',                                   r"\(Exile all spells and abilities from the stack. Discard down to your maximum hand size. Damage wears off, and \"this turn\" and \"until end of turn\" effects end\.\)"),
    rm(fr'[Ee]nlist',                                         fr"\(As this creature attacks, you may tap a nonattacking creature you control without summoning sickness. When you do, add its power to this creature's until end of turn\.\)"),
    rm(fr'[Ee]ntwine',                                        fr"\(Choose both if you pay the entwine cost\.\)"),
    rm(fr'[Ee]pic',                                           r"\(For the rest of the game, you can't cast spells. At the beginning of each of your upkeeps, copy this spell except for its epic ability\.(?: You may choose a new target for the copy\.)?\)"),
    rm(fr'[Ee]quip',                                          fr"\((?:{MTG_SYMBOL_REGEX})+: Attach to target creature you control. Equip only as a sorcery\.(?: This card enters the battlefield unattached and stays on the battlefield if the creature leaves\.)?\)"),
    rm(fr'[Ee]scalate',                                       r"\(Pay this cost for each mode chosen beyond the first\.\)"),
    rm(fr'[Ee]scape',                                         r"\(You may cast this card from your graveyard for its escape cost\.\)"),
    rm(fr'[Ee]ternalize',                                     fr"\((?:{MTG_SYMBOL_REGEX})+, Exile this card from your graveyard: Create a token that's a copy of it, except it's a 4/4 black Zombie [\w ]+ with no mana cost. Eternalize only as a sorcery\.\)"),
    rm(fr'[Ee]voke',                                          r"\(You may cast this spell for its evoke cost. If you do, it's sacrificed when it enters the battlefield\.\)"),
    rm(fr'[Ee]volve',                                         r"\(Whenever a creature enters the battlefield under your control, if that creature has greater power or toughness than this creature, put a \+1\/\+1 counter on this creature\.\)"),
    rm(fr'[Ee]xalted',                                        r"\(Whenever a creature(?: you control)? attacks alone, (?:it|that creature) gets \+1\/\+1 until end of turn(?: for each instance of exalted among permanents its controller controls)?\.\)"),
    rm(fr'[Ee]xert',                                          r"\((?:An exerted creature|It) won't untap during your next untap step\.\)"),
    rm(fr'[Ee]xploit',                                        r"\(When this creature enters the battlefield, you may sacrifice a creature\.\)"),
    rm(fr'[Ee]xplore',                                        r"\(Reveal the top card of your library. Put that card into your hand if it's a land. Otherwise, put a \+1\/\+1 counter on this creature, then put the card back or put it into your graveyard\.\)"),
    rm(fr'[Ee]xtort',                                         r"\(Whenever you cast a spell, you may pay {W\/B}. If you do, each opponent loses 1 life and you gain that much life\.\)"),
    rm(fr'[Ff]abricate',                                      r"\(When this creature enters the battlefield, put (?:a|\d+) \+1\/\+1 counters? on it or create (?:a|\d+) 1\/1 colorless Servo artifact creature tokens?\.\)"),
    rm(fr'[Ff]ading',                                         fr"\((?:This \w+|This|It|You|They) enters the battlefield with \d+ fade counters on it. At the beginning of your upkeep, remove a fade counter from it. If you can't, sacrifice it\.\)"),
    rm(fr'[Ff]ear',                                           r"\((?:This creature|This|It|You|They) can't be blocked except by artifact creatures and/or black creatures\.\)"),
    rm(fr'[Ff]ight',                                          r"\(Each deals damage equal to its power to the other\.\)"),
    rm(fr'[Ff]irst strike',                                   r"\((?:This creature|This|It|You|They) deals combat damage before creatures without first strike[^\n\)]*\)"),
    rm(fr'[Ff]lanking',                                       r"\(Whenever a creature without flanking blocks (?:this creature|[\w ]+), the blocking creature gets \-1\/\-1 until end of turn\.\)"),
    rm(fr'[Ff]lash',                                          r"\(You may cast (it|this spell) any time you could cast an instant\.\)"),
    rm(fr'[Ff]lashback',                                      r"\(You may cast this card from your graveyard for its flashback cost. Then exile it\.\)"),
    rm(fr'[Ff]lying',                                         r"\((?:This creature|This|It|You|They)(?: creature)? can't be blocked except by creatures with flying or reach\.\)"),
    rm(fr'[Ff]ood token',                                     r"\((It's|They're)(?: an)? artifacts? with \"\{2\}, \{T\}, Sacrifice this artifact: You gain 3 life\.\"\)"),
    rm(fr'[Ff]orestcycling',                                  fr"\((?:{MTG_SYMBOL_REGEX})+, Discard this card: Search your library for a Forest card, reveal it, put it into your hand, then shuffle\.\)"),
    rm(fr'[Ff]orestwalk',                                     r"\((?:They|It|You|This creature) can't be blocked as long as defending player controls a Forest\.\)"),
    rm(fr'[Ff]orecast',                                       r"\(Activate only during your upkeep and only once each turn\.\)"),
    rm(fr'[Ff]oretell',                                       r"\(During your turn, you may pay \{2\} and exile this card from your hand face down. Cast it on a later turn for its foretell cost\.\)"),
    rm(fr'[Ff]riends forever',                                fr"\(You can have 2 commanders if both have friends forever\.\)"),
    rm(fr'[Ff]use',                                           r"\(You may cast 1 or both halves of this card from your hand\.\)"),
    rm(fr'[Gg]oad',                                           r"\(Until your next turn, (?:this creature|that creature|those creatures|this|it|you|they) attacks? each combat if able and attacks? a player other than you if able\.\)"),
    rm(fr'[Gg]oad(?:ed)?',                                    r"\((?:This creature|That creature|This|It|You|They) attacks each combat if able and attacks a player other than you if able\.\)"),
    rm(fr'[Gg]raft',                                          fr"\(This creature enters the battlefield with \d+ \+1\/\+1 counters on it. Whenever another creature enters the battlefield, you may move a \+1\/\+1 counter from this creature onto it\.\)"),
    rm(fr'[Hh]aste',                                          r"\((?:This creature|This|It|You|They) can attack and \{T\} this turn\.\)"),
    rm(fr'[Hh]aste',                                          r"\((?:This creature|This|It|You|They) can attack and {T} as soon as it comes under your control\.\)"),
    rm(fr'[Hh]aunt',                                          fr"\((?:When this creature dies|When this spell card is put into a graveyard after resolving), exile it haunting target creature\.\)"),
    rm(fr'[Hh]exproof',                                       r"\((?:This creature|This|It|You|They) can't be the targets? of spells or abilities your opponents control\.\)"),
    rm(fr'[Hh]idden agenda',                                  r"\(Start the game with this conspiracy face down in the command zone and secretly choose a card name. You may turn this conspiracy face up any time and reveal that name\.\)"),
    rm(fr'[Hh]ideaway',                                       r"\(When this (?:land|enchantment) enters the battlefield, look at the top \d+ cards of your library, exile 1 face down, then put the rest on the bottom in a random order\.\)"),
    rm(fr'[Hh]orsemanship',                                   r"\((?:This creature|This|It|You|They) can't be blocked except by creatures with horsemanship\.\)"),
    rm(fr'[Ii]mprovise',                                      r"\(Your artifacts can help cast this spell. Each artifact you tap after you're done activating mana abilities pays for \{1\}\.\)"),
    rm(fr'[Ii]ndestructible',                                 fr"\((?:Damage and e|E)ffects that say \"destroy\" don't destroy (?:it|this|them|you)\.?(?: (?:creature|artifact)\.)?(?: If its toughness is 0 or less, it's still put into its owner's graveyard\.)?\)"),
    rm(fr'[Ii]nfect',                                         r"\((?:This creature|This|It|You|They) deals damage to creatures in the form of \-1\/\-1 counters and to players in the form of poison counters\.\)"),
    rm(fr'[Ii]ngest',                                         r"\(Whenever this creature deals combat damage to a player, that player exiles the top card of their library\.\)"),
    rm(fr'[Ii]ntimidate',                                     r"\((?:This creature|This|It|You|They) can't be blocked except by artifact creatures and\/or creatures that share a color with it\.\)"),
    rm(fr'[Ii]nvestigate',                                    fr"\(Create a Clue token. It's an artifact with \"(?:{MTG_SYMBOL_REGEX})+, Sacrifice this artifact: Draw a card\.\"\)"),
    rm(fr'[Ii]slandcycling',                                  fr"\((?:{MTG_SYMBOL_REGEX})+, Discard this card: Search your library for a Island card, reveal it, put it into your hand, then shuffle\.\)"),
    rm(fr'[Ii]slandwalk',                                     r"\((?:They|It|You|This creature) can't be blocked as long as defending player controls an Island\.\)"),
    rm(fr'[Jj]ump-start',                                     r"\(You may cast this card from your graveyard by discarding a card in addition to paying its other costs. Then exile this card\.\)"),
    rm(fr'[Kk]icker',                                         fr"\(You may (?:sacrifice (?:a|\d+) \w+s? in addition to any other costs|pay an additional (?:{MTG_SYMBOL_REGEX})+(?: and\/or (?:{MTG_SYMBOL_REGEX})+)?) as you cast this spell\.\)"),
    rm(fr'[Ll]ast strike',                                    r"\(This creature deals combat damage after creatures without last strike\.\)"),
    rm(fr'[Ll]earn',                                          r"\(You may reveal a Lesson card you own from outside the game and put it into your hand, or discard a card to draw a card\.\)"),
    rm(fr'[Ll]evel up',                                       fr"\((?:{MTG_SYMBOL_REGEX})+: Put a level counter on this. Level up only as a sorcery\.\)"),
    rm(fr'[Ll]ifelink',                                       r"\(Damage dealt by (the|this) creature also causes (?:its controller|you) to gain that much life\.\)"),
    rm(fr'[Ll]iving weapon',                                  r"\(When this Equipment enters the battlefield, create a 0\/0 black Phyrexian Germ creature token, then attach this to it\.\)"),
    rm(fr'[Mm]adness',                                        r"\(If you discard this card, discard it into exile. When you do, cast it for its madness cost or put it into your graveyard\.\)"),
    rm(fr'[Mm]anifest',                                       r"\(Put it onto the battlefield face down as a 2/2 creature. Turn it face up any time for its mana cost if it's a creature card\.\)"),
    rm(fr'[Mm]anifest',                                       r"\(To manifest a card, put it onto the battlefield face down as a 2\/2 creature. Turn it face up any time for its mana cost if it's a creature card\.\)"),
    rm(fr'[Mm]egamorph',                                      fr"\(You may cast this card face down as a 2\/2 creature for (?:{MTG_SYMBOL_REGEX})+. Turn it face up any time for its megamorph cost and put a \+1\/\+1 counter on it\.\)"),
    rm(fr'[Mm]elee',                                          r"\(Whenever this creature attacks, it gets \+\d+\/\+\d+ until end of turn for each opponent you attacked this combat\.\)"),
    rm(fr'[Mm]enace',                                         r"\((?:This creature|This|It|You|They) can't be blocked except by 2 or more creatures\.\)"),
    rm(fr'[Mm]entor',                                         r"\(Whenever this creature attacks, put a \+1\/\+1 counter on target attacking creature with lesser power\.\)"),
    rm(fr'[Mm]ill',                                           fr"\((?:To mill a card, a player|You may|They) puts? the top(?: \d+)? cards? of (?:their|your) library into (?:their|your) graveyard\.\)"),
    rm(fr'[Mm]iracle',                                        fr"\(You may cast this card for its miracle cost when you draw it if it's the first card you drew this turn\.\)"),
    rm(fr'[Mm]odular',                                        fr"\((?:This creature|This|It|You|They) enters? the battlefield with (?:a|\d+) \+1\/\+1 counters? on it. When it dies, you may put its \+1\/\+1 counters on target artifact creature\.\)"),
    rm(fr'[Mm]onstrosity',                                    r"\(If this creature isn't monstrous, put (?:X|\d+) \+1\/\+1 counters on it and it becomes monstrous\.\)"),
    rm(fr'[Mm]orph',                                          fr"\(You may cast this card face down as a 2\/2 creature for (?:{MTG_SYMBOL_REGEX})+. Turn it face up any time for its morph cost\.\)"),
    rm(fr'[Mm]ountaincycling',                                fr"\((?:{MTG_SYMBOL_REGEX})+, Discard this card: Search your library for a Mountain card, reveal it, put it into your hand, then shuffle\.\)"),
    rm(fr'[Mm]ountainwalk',                                   r"\((?:They|It|You|This creature) can't be blocked as long as defending player controls a Mountain\.\)"),
    rm(fr'[Mm]ore Than Meets the Eye',                        r"\(You may cast this card converted for (?:{MTG_SYMBOL_REGEX})+\.\)"),
    rm(fr'[Mm]ultikicker',                                    fr"\(You may pay an additional (?:{MTG_SYMBOL_REGEX})+ any number of times as you cast this spell\.\)"),
    rm(fr'[Mm]utate',                                         fr"\(If you cast this spell for its mutate cost, put it over or under target non-\w+ creature you own. They mutate into the creature on top plus all abilities from under it\.\)"),
    rm(fr'[Mm]yriad',                                         r"\(Whenever this creature attacks, for each opponent other than defending player, you may create a token that's a copy of this creature that's tapped and attacking that player or a planeswalker they control. Exile the tokens at end of combat\.\)"),
    rm(fr'[Nn]injutsu',                                       fr"\((?:{MTG_SYMBOL_REGEX})+, Return an unblocked attacker you control to hand: Put this card onto the battlefield from your hand tapped and attacking\.\)"),
    rm(fr'[Oo]pen an Attraction',                             r"\(Put the top card of your Attraction deck onto the battlefield\.\)"),
    rm(fr'[Oo]utlast',                                        fr"\((?:{MTG_SYMBOL_REGEX})+, "r"\{T\}"fr": Put a \+1\/\+1 counter on this creature. Outlast only as a sorcery\.\)"),
    rm(fr'[Oo]verload',                                       fr"\(You may cast this spell for its overload cost. If you do, change its text by replacing all instances of \"target\" with \"each\.\"\)"),
    rm(fr'[Pp]artner with',                                   r"\(When this creature enters the battlefield, target player may put [\w ]+ into their hand from their library, then shuffle\.\)"),
    rm(fr'[Pp]artner',                                        r"\(You can have 2 commanders if both have partner\.\)"),
    rm(fr'[Pp]oison',                                         r"\((?:Whenever it deals combat damage to a player, that player gets \d poison counters. )?A player with 10 or more poison counters loses the game\.\)"),
    rm(fr'[Pp]ersist',                                        r"\(When this creature dies, if it had no \-1\/\-1 counters on it, return it to the battlefield under its owner's control with a \-1\/\-1 counter on it\.\)"),
    rm(fr'[Pp]hasing',                                        r"\((?:This creature|This|It|You|They) phases in or out before you untap during each of your untap steps. While it's phased out, it's treated as though it doesn't exist\.\)"),
    rm(fr'[Pp]lainscycling',                                  fr"\((?:{MTG_SYMBOL_REGEX})+, Discard this card: Search your library for a Plains card, reveal it, put it into your hand, then shuffle\.\)"),
    rm(fr'[Pp]lainswalk',                                     r"\((?:They|It|You|This creature) can't be blocked as long as defending player controls a Plains\.\)"),
    rm(fr'[Pp]opulate',                                       r"\((?:To populate, c|C)reate a token that's a copy of a creature token you control\.(?: Do this (?:\d+|X) times\.)?\)"),
    rm(fr'[Pp]roliferate',                                    r"\(Choose any number of permanents and/or players, then give each another counter of each kind already there\.\)"),
    rm(fr'[Pp]rotection from (?:black|white|blue|green|red)', r"\((?:This creature|This|It|You|They) can't be blocked, targeted, dealt damage, (?:enchanted, or equipped|or enchanted) by anything (?:black|white|blue|green|red)\.\)"),
    rm(fr'[Pp]rovoke',                                        r"\(Whenever this creature attacks, you may have target creature defending player controls untap and block it if able\.\)"),
    rm(fr'[Pp]rowess',                                        r"\(Whenever you cast a noncreature spell, this creature gets \+1\/\+1 until end of turn\.\)"),
    rm(fr'[Pp]rowl',                                          r"\(You may cast this for its prowl cost if you dealt combat damage to a player this turn with a \w+(?: or \w+)?\.\)"),
    rm(fr'[Rr]ampage',                                        fr"\(Whenever this creature becomes blocked, it gets \+\d+\/\+\d+ until end of turn for each creature blocking it beyond the first\.\)"),
    rm(fr'[Rr]avenous',                                       r"\((?:This creature|This|It|You|They) enters? the battlefield with X \+1\/\+1 counters on it. If X is 5 or more, draw a card when it enters\.\)"),  # consider leaving this one in place due to using X, to  teach the AI that X needs a definition
    rm(fr'[Rr]each',                                          r"\((?:This creature|This|It|You|They) can block creatures with flying\.\)"),
    rm(fr'[Rr]ead ahead',                                     r"\(Choose a chapter and start with that many lore counters. Add 1 after your draw step. Skipped chapters don't trigger. Sacrifice after III\.\)"),
    rm(fr'[Rr]ebound',                                        r"\(If you cast this spell from your hand, exile it as it resolves. At the beginning of your next upkeep, you may cast this card from exile without paying its mana cost\.\)"),
    rm(fr'[Rr]econfigure',                                    fr"\((?:{MTG_SYMBOL_REGEX})+: Attach to target creature you control; or unattach from a creature. Reconfigure only as a sorcery. While attached, this isn't a creature\.\)"),
    rm(fr'[Rr]egenerate',                                     r"\(The next time (?:this|that) creature would be destroyed this turn, it isn't. Instead tap it, remove all damage from it, and remove it from combat\.\)"),
    rm(fr'[Rr]einforce',                                      fr"\((?:{MTG_SYMBOL_REGEX})+, Discard this card: Put (?:a|\d+|X) \+1\/\+1 counters? on target creature\.\)"),
    rm(fr'[Rr]enown',                                         fr"\(When this creature deals combat damage to a player, if it isn't renowned, put (?:a|\d+) \+1\/\+1 counters? on it and it becomes renowned\.\)"),
    rm(fr'[Rr]eplicate',                                      fr"\(When you cast this spell, copy it for each time you paid its replicate cost\.(?: You may choose new targets for the copies\.)?\)"),
    rm(fr'[Rr]etrace',                                        r"\(You may cast this card from your graveyard by discarding a land card in addition to paying its other costs\.\)"),
    rm(fr'[Rr]iot',                                           r"\((?:This creature|This|It|You|They) enters the battlefield with your choice of a \+1\/\+1 counter or haste\.\)"),
    rm(fr'[Rr]ipple',                                         fr"\(When you cast this spell, you may reveal the top \d+ cards of your library. You may cast spells with the same name as this spell from among those cards without paying their mana costs. Put the rest on the bottom of your library\.\)"),
    rm(fr'[Ss]cavenge',                                       fr"\((?:{MTG_SYMBOL_REGEX})+, Exile this card from your graveyard: Put a number of \+1\/\+1 counters equal to this card's power on target creature. Scavenge only as a sorcery\.\)"),
    rm(fr'[Ss]cry',                                           r"\((?:To scry \d+, l|L)ook at the top(?: \d+)? cards? of your library(?:, then(?: you may)?|. You may) put (?:any number of them|that card) on the bottom of your library(?: and the rest on top in any order)?\.\)"),
    rm(fr'[Ss]hadow',                                         r"\((?:This creature|This|It|You|They) can block or be blocked by only creatures with shadow\.\)"),
    rm(fr'[Ss]hield',                                         r"\(If it would be dealt damage or destroyed, remove a shield counter from it instead\.\)"),
    rm(fr'[Ss]hroud',                                         r"\((?:This creature|This|It|You|They) can't be the targets? of spells or abilities\.\)"),
    rm(fr'[Ss]kulk',                                          r"\((?:This creature|This|It|You|They) can't be blocked by creatures with greater power\.\)"),
    rm(fr'[Ss]oulbond',                                       r"\(You may pair this creature with another unpaired creature when either enters the battlefield. They remain paired for as long as you control both of them\.\)"),
    rm(fr'[Ss]oulshift',                                      fr"\(When this creature dies, you may return target Spirit card with mana value \d+ or less from your graveyard to your hand\.\)"),
    rm(fr'[Ss]pectacle',                                      r"\(You may cast this spell for its spectacle cost rather than its mana cost if an opponent lost life this turn\.\)"),
    rm(fr'[Ss]plice onto Arcane',                             r"\(As you cast an Arcane spell, you may reveal this card from your hand and pay its splice cost. If you do, add this card's effects to that spell\.\)"),
    rm(fr'[Ss]plit second',                                   r"\(As long as this spell is on the stack, players can't cast spells or activate abilities that aren't mana abilities\.\)"),
    rm(fr'[Ss]quad',                                          fr"\(As an additional cost to cast this spell, you may pay (?:{MTG_SYMBOL_REGEX})+ any number of times. When this creature enters the battlefield, create that many tokens that are copies of it\.\)"),
    rm(fr'[Ss]torm',                                          r"\(When you cast this spell, copy it for each spell cast before it this turn.(?: You may choose new targets for the copies\.)?\)"),
    rm(fr'[Ss]unburst',                                       r"\((?:This(?: creature)?|It|You) enters the battlefield with a (?:charge|\+1\/\+1) counter on it for each color of mana spent to cast it\.\)"),
    rm(fr'[Ss]upport',                                        fr"\(Put a \+1\/\+1 counter on each of up to \d+(?: other)? target creatures\.\)"),
    rm(fr'[Ss]urge',                                          r"\(You may cast this spell for its surge cost if you or a teammate has cast another spell this turn\.\)"),
    rm(fr'[Ss]urveil',                                        fr"\(Look at the top \d+ cards of your library, then put any number of them into your graveyard and the rest on top of your library in any order\.\)"),
    rm(fr'[Ss]urveil',                                        r"\((?:To surveil \d+, l|L)ook at the top(?: \d+)? cards? of your library. You may put (?:any number of them|that card) into your graveyard(?: and the rest on top of your library in any order)?\.\)"),
    rm(fr'[Ss]uspend',                                        fr"\(Rather than cast this card from your hand,(?: you may)? pay (?:{MTG_SYMBOL_REGEX})+ and exile it with (?:a|\d+) time counters? on it. At the beginning of your upkeep, remove a time counter. When the last is removed, cast it without paying its mana cost\.(?: It has haste\.)?\)"),
    rm(fr'[Ss]wampcycling',                                   fr"\((?:{MTG_SYMBOL_REGEX})+, Discard this card: Search your library for a Swamp card, reveal it, put it into your hand, then shuffle\.\)"),
    rm(fr'[Ss]wampwalk',                                      r"\((?:They|It|You|This creature) can't be blocked as long as defending player controls a Swamp\.\)"),
    rm(fr'[Tt]otem armor',                                    r"\(If enchanted creature would be destroyed, instead remove all damage from it and destroy this Aura\.\)"),
    rm(fr'[Tt]raining',                                       r"\(Whenever this creature attacks with another creature with greater power, put a \+1/\+1 counter on this creature\.\)"),
    rm(fr'[Tt]rample',                                        r"\((?:This creature|This|It|You|They)( creature)? can deal excess combat damage to the player or planeswalker it's attacking\.\)"),
    rm(fr'[Tt]ransmute',                                      fr"\((?:{MTG_SYMBOL_REGEX})+, Discard this card: Search your library for a card with the same mana value as this card, reveal it, put it into your hand, then shuffle. Transmute only as a sorcery\.\)"),
    rm(fr'[Tt]reasure token',                                 r"\((?:It's|They're)(?: an)? artifacts? with \"\{T\}, Sacrifice this artifact: Add 1 mana of any color\.\"\)"),
    rm(fr'[Tt]ribute',                                        fr"\(As this creature enters the battlefield, an opponent of your choice may put \d+ \+1\/\+1 counters on it\.\)"),
    rm(fr'[Uu]ndaunted',                                      fr"\(This spell costs (?:{MTG_SYMBOL_REGEX})+ less to cast for each opponent\.\)"),
    rm(fr'[Uu]ndying',                                        r"\(When this creature dies, if it had no \+1\/\+1 counters on it, return it to the battlefield under its owner's control with a \+1\/\+1 counter on it\.\)"),
    rm(fr'[Uu]nearth',                                        fr"\((?:{MTG_SYMBOL_REGEX})+: Return this card from your graveyard to the battlefield. It gains haste. Exile it at the beginning of the next end step or if it would leave the battlefield. Unearth only as a sorcery\.\)"),
    rm(fr'[Uu]nleash',                                        r"\(You may have this creature enter the battlefield with a \+1\/\+1 counter on it. It can't block as long as it has a \+1/\+1 counter on it\.\)"),
    rm(fr'[Vv]anishing',                                      fr"\((?:This creature|This|It|You|They) enters the battlefield with (?:a|\d+) time counters? on it. At the beginning of your upkeep, remove a time counter from it. When the last is removed, sacrifice it\.\)"),
    rm(fr'[Vv]enture into the dungeon',                       r"\(Enter the first room or advance to the next room\.\)"),
    rm(fr'[Vv]igilance',                                      r"\(Attacking doesn't cause (it|this creature) to tap\.\)"),
    rm(fr'[Ww]ard',                                           fr"\(Whenever (?:equipped|this) creature becomes the target of a spell or ability an opponent controls, counter it unless that player pays (?:\d+ life|(?:{MTG_SYMBOL_REGEX})+)\.\)"),
    rm(fr'[Ww]ither',                                         r"\((?:This creature|This|It|You|They|A source with wither) deals? damage to creatures in the form of \-1\/\-1 counters\.\)"),
    rm(fr'loses all other card types',                        r"\(It still has its abilities, but it's no longer a \w+\.\)"),
    rm(fr'phases out',                                        fr"\(Treat it and anything attached to it as though they don't exist until its controller's next turn\.\)"),
    rm(fr'phases out',                                        fr"\(While it's phased out, it's treated as though it doesn't exist. It phases in before you untap during your next untap step\.\)"),
]


def XYZ_variable_capitalize(s):
    # Capitalize all X's, Y's, and Z's, when acting as variables
    variable_x_regex = r'((?<=^)|(?<=[\s\+\-\/\{]))([xXyYzZ])(?=$|[\s:,\.\/\}])'
    capitalize = lambda x: x.group(2).upper()
    return re.sub(variable_x_regex, capitalize, s)


def deduplicate_cards(cards):
    # consumes list of internal formats, returns list of internal formats
    # drops identical copies of cards
    # omits rarity in compared fields
    #   In the case that rarity is the only distinction between two cards, arbitrarily picks the first one in the input list

    # for performance reasons, group cards by name, and down-select within each name group
    #   this produces identical results since the name field is compared anyway
    # each name group may contribute multiple down-selected cards
    #   and that is expected since some cards have been rebalanced, resulting in technical differences in important fields such as cost or main_text
    #   we are intentionally keeping each card with even slight variations
    # can't use a set to deduplicate because dict's aren't hashable
    groups = defaultdict(list)
    for card in cards:
        groups[card['name']].append(card)

    unique_cards = []
    for name, group in groups.items():
        unique_group = []
        for card in group:
            card_restricted = {k:v for k,v in card.items() if k not in ['rarity']}
            if card_restricted not in unique_group:
                unique_group.append(card_restricted)
                unique_cards.append(card)

    return unique_cards


def limit_to_AI_training_cards(cards):
    # consumes list of internal formats, returns list of internal formats
    # drops those cards which are not suitable for the AI to train with

    # TODO
    limited_cards = cards

    return limited_cards


def json_to_internal_format(json_path):
    # consumes AllPrintings.json, produces list of internally formated cards
    # deduplicates cards that repeat. See deduplicate_cards() for details
    # Docs for AllPrintings.json are located here: https://mtgjson.com/data-models/card-set/ etc
    #   we're iterating over 'Set' and then 'Card (Set)' objects, as defined by those docs

    f = open(json_path)
    j = json.load(f)
    f.close()

    cards = []

    for k_set, v_set in list(j['data'].items()):
        # collect set cards first, to make correct b-side associations
        # then add these to the aggregate set above
        primary_sides = []
        non_primary_sides = []

        # this is a big and complicated dataset, so lets make sure the list of available information matches our expectations
        expected_keys = ['baseSetSize', 'cards', 'code', 'isFoilOnly', 'isOnlineOnly', 'keyruneCode', 'name', 'releaseDate', 'tokens', 'totalSetSize',
                         'translations', 'type',
                        ]
        optional_keys = ['block', 'booster', 'cardsphereSetId', 'codeV3', 'isForeignOnly', 'isNonFoilOnly', 'isPaperOnly', 'isPartialPreview', 'mcmId',
                         'mcmIdExtras', 'mcmName', 'mtgoCode', 'parentCode', 'sealedProduct', 'tcgplayerGroupId',
                        ]
        for k in expected_keys: assert k in v_set, k
        for k in v_set: assert k in expected_keys or k in optional_keys, k

        for j_card in v_set['cards']:
            # this is a big and complicated dataset, so lets make sure the list of available information matches our expectations
            expected_keys = ['availability', 'borderColor', 'colorIdentity', 'colors', 'finishes', 'foreignData', 'frameVersion', 'identifiers', 'language',
                             'layout', 'legalities', 'manaValue', 'name', 'number', 'purchaseUrls', 'rarity', 'rulings', 'setCode', 'subtypes', 'supertypes',
                             'type', 'types', 'uuid',
                            ]
            deprecated_keys = ['convertedManaCost', 'hasFoil', 'hasNonFoil',]
            optional_keys = ['artist', 'asciiName', 'boosterTypes', 'cardParts', 'colorIndicator', 'edhrecRank', 'faceConvertedManaCost', 'faceFlavorName',
                             'faceManaValue', 'faceName', 'flavorName', 'flavorText', 'frameEffects', 'hand', 'hasAlternativeDeckLimit', 'hasContentWarning',
                             'isAlternative', 'isFullArt', 'isFunny', 'isOnlineOnly', 'isOversized', 'isPromo', 'isRebalanced', 'isReprint', 'isReserved',
                             'isStarter', 'isStorySpotlight', 'isTextless', 'isTimeshifted', 'keywords', 'leadershipSkills', 'life', 'loyalty', 'manaCost',
                             'originalPrintings', 'originalReleaseDate', 'originalText', 'originalType', 'otherFaceIds', 'power', 'printings', 'promoTypes',
                             'rebalancedPrintings', 'securityStamp', 'side', 'signature', 'text', 'toughness', 'variations', 'watermark',
                            ]
            undocumented_keys = ['attractionLights', 'duelDeck', 
                                ]
            for k in expected_keys: assert k in j_card, k + str(j_card)
            for k in j_card: assert k in expected_keys or k in deprecated_keys or k in optional_keys or k in undocumented_keys, k + str(j_card)

            # create a backlink from the card object to its set
            j_card['set'] = v_set

            # write card fields
            # json_fields is a temporary field which will be removed at the end of this process
            card = {'json_fields': j_card}

            # name
            if 'faceName' in j_card:
                card['name'] = j_card['faceName']
            else:
                card['name'] = j_card['name']

            # main_text. json property 'isTextless' is sometimes not correct, so don't use it
            if 'text' in j_card:
                card['main_text'] = j_card['text']
            elif 'originalText' in j_card:
                card['main_text'] = j_card['originalText']
            else:
                card['main_text'] = None
            card['main_text'] = card['main_text'] or None  # handle empty strings, if any

            # cost
            if 'manaCost' in j_card:
                card['cost'] = j_card['manaCost']
            else:
                card['cost'] = None

            # power_toughness
            assert (('power' in j_card and 'toughness' in j_card)
                 or ('power' not in j_card and 'toughness' not in j_card))
            if 'power' in j_card:
                card['power_toughness'] = [j_card['power'],
                                           j_card['toughness']]
            else:
                card['power_toughness'] = None

            # loyalty
            if 'loyalty' in j_card:
                card['loyalty'] = j_card['loyalty']
            else:
                card['loyalty'] = None

            # flavor
            if 'flavorText' in j_card:
                card['flavor'] = j_card['flavorText']
            else:
                card['flavor'] = None
            
            # rarity
            card['rarity'] = j_card['rarity']

            # types
            card['type'] = j_card['type']

            # assign as primary or non-primary card sides. Non-primary card sides will be sorted into their primaries later
            if 'side' in j_card and j_card['side'] in ['b', 'c', 'd', 'e']:
                assert 'otherFaceIds' in j_card
                non_primary_sides.append(card)
            else:
                primary_sides.append(card)

        # assign non_primary_sides to their primary side
        for np_card in non_primary_sides:
            for p_card in primary_sides:
                if p_card['json_fields']['uuid'] in np_card['json_fields']['otherFaceIds']:
                    p_card[np_card['json_fields']['side'] + '_side'] = np_card
                    break
            else:
                raise ValueError(f"Primary card not found for \"{np_card['name']}\" {np_card['json_fields']['uuid']}")

        # verify b-e sides don't skip letters (always in order)
        for card in primary_sides:
            if 'c_side' in card: assert 'b_side' in card 
            if 'd_side' in card: assert 'c_side' in card 
            if 'e_side' in card: assert 'd_side' in card 

        # finally, remove the json_fields temporary key
        for card in primary_sides:
            del card['json_fields']
            if 'b_side' in card: del card['b_side']['json_fields']
            if 'c_side' in card: del card['c_side']['json_fields']
            if 'd_side' in card: del card['d_side']['json_fields']
            if 'e_side' in card: del card['e_side']['json_fields']

        cards.extend(primary_sides)

    return cards


def pairs(x):
    # returns list of pairs of elements of x with no repeats
    #   eg [(x[0], x[1]), (x[2], x[3]), ...]

    for i, y in enumerate(itertools.pairwise(x)):
        # drop the odd yields from itertools.pairwise
        if i%2:
            continue

        yield y


def in_reserved_word(s):
    # returns boolean indicating whether s is or is a subset of any reserved keyword
    # be careful that some simple words like 'the' appear in keywords

    s = s.lower()

    for reserved in MTG_KEYWORDS + MTG_TYPE_WORDS:
        if s in reserved:
            return True
    return False


def ends_reserved_word(s):
    # returns boolean indicating whether and reserved keywords ends in s
    s = s.lower()
    for reserved in MTG_KEYWORDS + MTG_TYPE_WORDS:
        if reserved.endswith(s):
            return True
    return False


def begins_reserved_word(s):
    # returns boolean indicating whether and reserved keywords begin in s
    s = s.lower()
    for reserved in MTG_KEYWORDS + MTG_TYPE_WORDS:
        if reserved.startswith(s):
            return True
    return False


def all_contiguous_subsets(x, even_boundary_conditions=False):
    # generates all contiguous subsets of an iterable x
    #   largest substrings are yielded first
    #   even_boundary_conditions => only yields subsets with even indexed boundries
    # eg ['a', 'b', 'c'] -> [['a', 'b', 'c'], ['a', 'b'], ['b', 'c'], ['a'], ['b'], ['c']]
    # or with even_boundary_conditions ['a', 'b', 'c', 'd'] -> [['a', 'b', 'c'], ['a'], ['c']]

    # collect all start + end pairs, and then sort by longest ranges
    # this extra sort step gives us longest subsets first
    indeces = []
    for start in range(len(x)):
        if even_boundary_conditions and start%2:
            continue
        for end in reversed(range(start, len(x))):
            if even_boundary_conditions and end%2:
                continue
            indeces.append([start, end])

    # sort by longest subsets first, then secondarily by earliest subset
    indeces.sort(key = lambda x: [x[1] - x[0], -x[0], -x[1]], reverse=True)

    for start, end in indeces:
        yield x[start: end + 1]


def is_small_word(s):
    return titlecase.SMALL_WORDS.search(s) is not None


def non_trivial_substrings(s):
    # returns list of all meaningful substrings of string s
    # each contiguous substring, broken only at word boundaries, is in the return list, as long as
    #   the subset contains atleast one non-small word
    #   first and last token are not small words
    #   the subset is not itself a subset of a reserved word in MTG
    #   is not numerical

    tokens = re.split(r'((?:(?<!\w)\-(?!\w)|[^\w@\-\+\/])+)', s)  # even tokens are words

    would_never_be_a_name_reference = ['You']

    for subset in all_contiguous_subsets(tokens, even_boundary_conditions=True):
        all_words_are_small = all([is_small_word(x) for i, x in enumerate(subset) if not i%2])  # even indeces are words, odd will be word separator characters
        sub_name = ''.join(subset)
        if (not all_words_are_small
            and not is_small_word(subset[0])
            and not is_small_word(subset[-1])
            and sub_name != ''
            and sub_name not in would_never_be_a_name_reference
            and not re.search(r'^[\-\+]?\d+$', sub_name)
            ):
            yield sub_name


def capture_named_context(name, text, start=0):
    # returns the first substring from text containing name, plus possibly some surrounding word(s) whenever
    #   surrounding words are capitalized
    #   includes uncapitalized small words, only when followed/preceeded eventually by a capitalized unreserved word
    #   but will not cross sentence boundaries
    # optionally starts looking at index start in text
    # returns None if there is no match for name in text beginning from start

    pretext = text[:start]
    text = text[start:]

    # break on word boundaries. '-' characters are tricky, let them be in words
    #   but otherwise treate them as non word characters when they exist outside or at the boundary of words
    name_tokens = re.split(r'((?:(?<!\w)\-(?!\w)|[^\w@\-\+\/])+)', name)  # even tokens are words
    text_tokens = re.split(r'((?:(?<!\w)\-(?!\w)|[^\w@\-\+\/])+)', text)  # even tokens are words

    # find start and end of name in text, counted in tokens
    def find_start(a, b):
        for i_token, token in enumerate(b):
            if token == a[0]:
                if all([(i_token + offset < len(b) and token2 == b[i_token + offset]) for offset, token2 in enumerate(a)]):
                    return i_token
        return None

    start = find_start(name_tokens, text_tokens)
    if start is None:
        return None
    end = start + len(name_tokens)

    def include_token(t, prev_token=None, direction='right'):
        if t == '':
            return False

        # check if capitalized
        if t[0] != t[0].upper():
            return False

        # check for capitalized words which are obviously not part of the name
        obviously_not_part_of_the_name = ['When', 'Whenever']
        # common_words_wont_be_used_as_name_reference = ['Black', 'Blue', 'White', 'Green', 'Red']
        if t in obviously_not_part_of_the_name:
            return False

        return True

    # add tokens to the right
    for i_token in range(end, len(text_tokens)):
        is_word = not i_token%2
        token = text_tokens[i_token]

        # mostly we don't process non-words.
        # But do look for boundaries we don't want to cross, such as end of sentences
        #   note that ',+()&' are intentionally not considered boundaries here, since names often contain these
        if not is_word:
            b = False
            for x in '[]{}:;?/\\-!•@\n—':
                if x in token:
                    b = True
                    break
            if b:
                break

            if token in [' - ']:
                break
            continue

        if is_small_word(token):
            continue
        elif include_token(token):
            end = i_token + 1
        else:
            break
    
    # add tokens to the left
    for i_token in range(start-1, -1, -1):
        is_word = not i_token%2
        token = text_tokens[i_token]

        # mostly we don't process non-words.
        # But do look for boundaries we don't want to cross, such as end of sentences
        #   note that ',+()&' are intentionally not considered boundaries here, since names often contain these
        if not is_word:
            b = False
            for x in '[]{}:;?/\\-!•@\n—':
                if x in token:
                    b = True
                    break
            if b:
                break

            if token in [' - ']:
                break
            continue

        prev_token = None
        if i_token > 0:
            prev_token = text_tokens[i_token - 1]
        if is_small_word(token):
            continue
        elif include_token(token, prev_token=prev_token, direction='left'):
            start = i_token
        else:
            break

    # calculate start / end as indeces into the text string
    start_str_index = len(pretext) + sum([len(text_tokens[i_token]) for i_token in range(0, start)])
    end_str_index = len(pretext) + start_str_index + sum([len(text_tokens[i_token]) for i_token in range(start, end)])

    return ''.join(text_tokens[start: end]), start_str_index, end_str_index


def temporarily_remove_reserved_words(s):
    # returns s where all keywords in s have been substituted with a unique reserved character
    # also returns list of substitutions, which will be needed as an arg to the reverse function
    regex = rf'(?:(?<=[\W])|(?<=^))({"|".join(MTG_KEYWORDS + MTG_TYPE_WORDS)})(?=\W|$)'
    reserved_char = '\u2014'  # we know this won't exist in the text when this function is used
    subs = re.findall(regex, s)
    return re.sub(regex, reserved_char, s), subs


def replace_temporarily_removed_reserved_words(s, subs):
    # returns s where all keywords have been replaced
    # reverse of temporarily_remove_reserved_words
    reserved_char = '\u2014'
    for sub in subs:
        s = s.replace(reserved_char, sub, 1)
    return s


def decimal_to_unary(s, mana=False):
    # s is string of decimal encoded integer
    # returns string of unary encoded integer

    if mana:
        prefix = '⓿'
    else:
        prefix = '⓪'

    # handle leading zeros
    if s[0] == '0' and len(s) > 1:
        return prefix + decimal_to_unary(s[1:], mana=mana)

    return prefix + '^' * int(s)


def unary_to_decimal(s):
    # s is string of unary encoded integer
    # returns string of decimal encoded integer

    return str(len(s))


class Number_Word_Converter():
    # converts number words to / from integers
    # eg '37' <-> 'thirty seven'

    def __init__(self):
        self._units = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight',
                  'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen',
                  'sixteen', 'seventeen', 'eighteen', 'nineteen',
        ]
        self._tens = ['twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']
        self._scales = ['hundred', 'thousand', 'million', 'billion', 'trillion']

        self.NUMBER_WORDS = self._units + self._tens + self._scales

        self._multiply = {}
        self._increment = {}

        for i_word, word in enumerate(self._units):
            self._increment[word] = i_word

        for i_word, word in enumerate(self._tens):
            self._increment[word] = (i_word + 2) * 10

        for i_word, word in enumerate(self._scales):
            if i_word == 0:
                self._multiply[word] = 10 ** 2
            else:
                self._multiply[word] = 10 ** (i_word * 3)

    def str_to_int(self, s):
        # eg 'thirty seven' -> '37'

        total = 0
        intermediate = 0
        for word in re.split(r'[ \-]', s.strip()):
            assert word in self.NUMBER_WORDS or word == 'and', 'Not a supported number word: ' + word

            multiply = self._multiply.get(word, 1)
            increment = self._increment.get(word, 0)
            intermediate = intermediate * multiply + increment

            if multiply > 100:
                total += intermediate
                intermediate = 0

        return str(total + intermediate)

    def int_to_str(s):
        # eg '37' -> 'thirty seven'

        s = str(s)  # allow actual integers as input
        l = len(s)

        words = []
        digits = ''
        for i_char, char in enumerate(s):
            reverse_i_char = l - i_char - 1

            scale = None
            if reverse_i_char > 2:
                scale = scales[reverse_i_char // 3]

            terminates_scale = not reverse_i_char % 3

            if not terminates_scale:
                digits += char

            else:
                if len(digits) == 3:
                    words.append(self._units[int(digits[0])])
                    words.append(self._scales[0])
                    digits = digits[1:]

                if int(digits) < 20:
                    words.append(self._units[int(digits)])
                else:
                    words.append(self._tens[int(digits[0] - 2)])
                    words.append(self._units[int(digits[1])])

                if scale is not None:
                    words.append(self._scales[scale])

                digits = ''

        return ' '.join(words)


nwc = Number_Word_Converter()


def internal_format_to_AI_format(card):
    # consumes list of internal formats, returns list of internal formats
    # consumes a single internal format, produces a single AI formatted string

    # convert fields to local variables, specifically do not edit input dict
    # add default values for AI fields when card fields are None
    cost            = card['cost'] or ''
    loyalty         = card['loyalty'] or ''
    main_text       = card['main_text'] or ''
    type_string     = card['type']
    name            = card['name']
    power_toughness = card['power_toughness'] or []
    rarity          = card['rarity']

    # encode rarity as unique symbols
    rarity = MTG_RARITY_JSON_TO_AI_FORMAT[rarity]

    # str encode the power and toughness
    power_toughness = '/'.join(power_toughness)

    # substitute card name with a unique character in main text so that there's only one copy of the full name for the AI to handle
    # skip this step if the card name is exactly equal to a reserved word / phrase
    # note this step is actually kinda difficult to get right, since
    #   keywords can be a subset of the name
    #   the name can be a subset of a keyword
    #   the name can be exactly a keyword (eg card named "Fear" uses keyword "Fear")
    #   so preventing accidental replacements of keywords while also replacing all names is difficult to verify
    if name not in MTG_KEYWORDS + MTG_TYPE_WORDS:
        main_text = main_text.replace(name, '@')

    # convert all fields to lowercase
    #   except mana costs
    #   and except variable usage of X, Y, and Z
    # Actually, getting correct capitalization in the reverse function is very difficult
    #   we can capitalize instances of the card name just fine, and characters beginning a sentence, after colons, etc
    #   but the hard part is made up proper names, partial name matches, types (usually), keywords (sometimes)
    #   the linguistical parsing is actually a fairly tough problem
    #   so we should let the AI handle capitialization entirely. It'll probably do better than we can
    # main_text = main_text.lower()
    # main_text = XYZ_variable_capitalize(main_text)
    # type_string = type_string.lower()
    # name = name.lower()
    # power_toughness = power_toughness.lower()

    # reduce character overloading for dashes
    # convert numerical minus signs to a unique character
    main_text = re.sub(r'(?<!\w)-(?=\d)', '∓', main_text)

    # encode symbols (including mana, excepting numerical) in AI format
    for a, b in MTG_SYMBOL_JSON_TO_AI_FORMAT.items():
        main_text = main_text.replace(a, b)
        cost = cost.replace(a, b)

    # encode numbers (including numerical mana) in every field to unary
    # mana
    cost = re.sub(r'\{(\d+)\}', lambda x: decimal_to_unary(x.group(1), mana=True), cost)
    main_text = re.sub(r'\{(\d+)\}', lambda x: decimal_to_unary(x.group(1), mana=True), main_text)
    # all remaining numbers
    name = re.sub(r'(\d+)', lambda x: decimal_to_unary(x.group(1)), name)
    loyalty = re.sub(r'(\d+)', lambda x: decimal_to_unary(x.group(1)), loyalty)
    main_text = re.sub(r'(\d+)', lambda x: decimal_to_unary(x.group(1)), main_text)
    power_toughness = re.sub(r'(\d+)', lambda x: decimal_to_unary(x.group(1)), power_toughness)

    # simplify repeated counter syntax, so the AI doesn't have to remember types once it specifies one
    # for each new counter type, encode it as 'type%'
    # repeated counters of the same type will be encoded simply as '%'
    reserved_char = '\u2014'  # we know this won't exist in the text when this function is used
    regex = fr'(?:(?<=^)|(?<=\W))({"|".join(MTG_COUNTERS)}) counter(?=$|\W)'
    subs = re.findall(regex, main_text)
    main_text = re.sub(regex, reserved_char, main_text)
    previous_counter = None
    for counter_type in subs:
        if counter_type == previous_counter:
            enc = '%'
        else:
            enc = f'{counter_type}%'
        main_text = main_text.replace(reserved_char, enc, 1)
        previous_counter = counter_type

    # standardize verbiage for countering spells to "uncast"
    #   this reduces overloading of the word "counter" for the AI
    # assume all uses of "counter" outside the list of MTG_COUNTERS is a verb
    main_text = re.sub(rf'(?<!{" )(?<!".join(MTG_COUNTERS)} )counter', 'uncast', main_text)
    main_text = re.sub(rf'(?<!{" )(?<!".join(MTG_COUNTERS)} )Counter', 'Uncast', main_text)

    # convert newlines to a unique character
    # we're going to reserve actual newlines for making the output file a bit more human readable
    main_text = main_text.replace('\n', '\\')

    # label fields for the AI
    #   this increases syntax, but regularizes AI output, so is a net win
    AI_string = f'{name}∥1{cost}∥2{type_string}∥3{loyalty}∥4{power_toughness}∥5{rarity}∥6{main_text}'

    # recurse on b-e sides
    if 'b_side' in card:
        AI_string += '␥' + internal_format_to_AI_format(card['b_side'])
    if 'c_side' in card:
        AI_string += '␥' + internal_format_to_AI_format(card['c_side'])
    if 'd_side' in card:
        AI_string += '␥' + internal_format_to_AI_format(card['d_side'])
    if 'e_side' in card:
        AI_string += '␥' + internal_format_to_AI_format(card['e_side'])

    return AI_string


def AI_to_internal_format(AI_string):
    # consumes a single AI formatted string, produces a single internally formatted card
    # runs error correction, parsing, and validation before returning the card
    # may raise errors during validation

    AI_string = error_correct_AI(AI_string)

    sides = AI_string.split('␥')
    assert sides

    # breakup fields
    card = {}
    fields = re.split(r'(∥\d)', sides[0])
    card['name'] = fields[0]

    field_names = {'∥1': 'cost', '∥2': 'type', '∥3': 'loyalty', '∥4': 'power_toughness', '∥5': 'rarity', '∥6': 'main_text'}
    for field_id, field in pairs(fields[1:]):
        field_name = field_names[field_id]
        card[field_name] = field

    for k, v in field_names.items():
        assert v in card, f'Failed to find field "{v}" in "{AI_string}" -> {fields}'

    # decode newlines
    card['main_text'] = card['main_text'].replace('\\', '\n')

    # decode rarity
    card['rarity'] = MTG_RARITY_AI_TO_JSON_FORMAT[card['rarity']]

    # revert uncast to counter
    card['main_text'] = card['main_text'].replace('uncast', 'counter')
    card['main_text'] = card['main_text'].replace('Uncast', 'Counter')

    # decode counter syntax to human readable format
    reserved_char = '\u2014'  # we know this won't exist in the text when this function is used
    regex = r'(\S*)%'
    subs = re.findall(regex, card['main_text'])
    card['main_text'] = re.sub(regex, reserved_char, card['main_text'])
    counter_type = None
    for new_type in subs:
        counter_type = new_type or counter_type
        assert counter_type is not None, card['main_text']  # don't let the AI not label the first counter
        card['main_text'] = card['main_text'].replace(reserved_char, f'{counter_type} counter', 1)

    # decode symbols (including mana, excepting numerical)
    for a, b in MTG_SYMBOL_AI_TO_JSON_FORMAT.items():
        card['main_text'] = card['main_text'].replace(a, b)

    for a, b in MTG_SYMBOL_AI_TO_JSON_FORMAT.items():
        card['cost'] = card['cost'].replace(a, b)

    # decode numbers (including numerical mana) in every field from unary
    # mana
    card['cost'] = re.sub(r'⓿(\^*)', lambda x: '{' + unary_to_decimal(x.group(1)) + '}', card['cost'])
    card['main_text'] = re.sub(r'⓿(\^*)', lambda x: '{' + unary_to_decimal(x.group(1)) + '}', card['main_text'])
    # all remaining numbers
    card['name'] = re.sub(r'⓪(\^*)', lambda x: unary_to_decimal(x.group(1)), card['name'])
    card['loyalty'] = re.sub(r'⓪(\^*)', lambda x: unary_to_decimal(x.group(1)), card['loyalty'])
    card['main_text'] = re.sub(r'⓪(\^*)', lambda x: unary_to_decimal(x.group(1)), card['main_text'])
    card['power_toughness'] = re.sub(r'⓪(\^*)', lambda x: unary_to_decimal(x.group(1)), card['power_toughness'])

    # reduce character overloading for dashes
    # convert numerical minus signs to a unique character
    card['main_text'] = re.sub(r'∓', '-', card['main_text'])

    # decode power toughness
    if card['power_toughness'] != '':
        card['power_toughness'] = card['power_toughness'].split('/')

    # replace backreferences to name
    card['main_text'] = card['main_text'].replace('@', card['name'])

    # insert None values instead of empty strings
    card['cost'] = card['cost'] or None
    card['loyalty'] = card['loyalty'] or None
    card['power_toughness'] = card['power_toughness'] or None
    card['main_text'] = card['main_text'] or None

    # recurse on b-e sides
    if len(sides) >= 2: card['b_side'] = AI_to_internal_format(sides[1])
    if len(sides) >= 3: card['c_side'] = AI_to_internal_format(sides[2])
    if len(sides) >= 4: card['d_side'] = AI_to_internal_format(sides[3])
    if len(sides) >= 5: card['e_side'] = AI_to_internal_format(sides[4])
    if len(sides) > 5:
        raise NotImplementedError('Too many sides, only implemented a-e sides')
    
    validate(card)
    return card


def validate(card):
    # consumes internal format, raises error on validation fail
    # should not raise error for all canonical cards, but may raise errors for AI generated cards
    
    # check that X has a definition if it is present anywhere

    # check that counters have a type definition (or are generic counters allowed?)

    # check that the only numbers that exist are 
    pass  # TODO


def error_correct_AI(AI_string):
    # consumes AI format, returns AI format with error corrections applied
    # OR maybe consumes internal format, returns internal format with error corrections applied
    # TODO

    # TODO strip string

    return AI_string


def unreversable_modifications(card):
    # consumes a single internal format, modifies it in place
    # makes changes which are not reversable by AI_to_internal_format
    #   such as stripping and enforcing repeatable capitalization
    # this function will return a dataset which can be directly compared to the dual_processed format for validity
    # since the changes made by this function are not validated by reversion, they should be reviewed by hand
    
    # TODO substitute dashes used to indicate a range
    #   eg 'Roll a d20...\n1–14 | Return all creature cards in your graveyard that were put there from the battlefield this turn to your hand.\n'
    
    # strip text fields
    card['name'] = card['name'].strip()
    if card['main_text'] is not None:
        card['main_text'] = card['main_text'].strip()
    if card['flavor'] is not None:
        card['flavor'] = card['flavor'].strip()

    # coerce some inconsistent rules text to improve parsing consistency for the AI
    if card['main_text'] is not None:
        card['main_text'] = card['main_text'].replace('(Its mana symbols remain unchanged.)', '(Mana symbols on that permanent remain unchanged.)')

    # coerce rarity to specific formatting
    # this creates a robust encoder -> decoder loop target
    card['rarity'] = card['rarity'].capitalize()
    if card['rarity'] == 'Mythic Rare':
        card['rarity'] = 'Mythic'

    # fix alchemy symbol prepended to card names
    card['name'] = re.sub(r'^A-', '', card['name'])

    # convert one-off large nubmers to strings, since numbers are reserved characters
    # normal (smaller) numbers will be converted to unary, but that doesn't make sense for these
    # there also aren't very many number above 20 actually used
    def sub_large_numbers(s):
        s = re.sub(r'100,?000(?![^\{]*\})', 'one-hundred-thousand', s)
        s = re.sub(r'1,?996(?![^\{]*\})', 'nineteen-ninety-six', s)  # date instead of amount?
        s = re.sub(r'1,?000(?![^\{]*\})', 'one-thousand', s)
        s = re.sub(r'200(?![^\{]*\})', 'two-hundred', s)
        s = re.sub(r'100(?![^\{]*\})', 'one-hundred', s)
        s = re.sub(r'50(?![^\{]*\})', 'fifty', s)
        s = re.sub(r'40(?![^\{]*\})', 'forty', s)
        s = re.sub(r'30(?![^\{]*\})', 'thirty', s)
        s = re.sub(r'25(?![^\{]*\})', 'twenty-five', s)
        return s

    card['name'] = sub_large_numbers(card['name'])
    if card['main_text'] is not None:
        card['main_text'] = sub_large_numbers(card['main_text'])

    # convert common unicode characters to ascii, both for standardization for the AI, and to reduce vocab size
    # a few of these characters are intentionally commented out, we specifically want those unicode characters to remain
    #   bullet: needs a unique replacement character anyway, so might as well use an actual bullet
    #   1/2: avoid overloading the meaning of numbers or '/' character for the AI
    #   inf: 
    def sub_unicode(s):
        s = s.replace('—',      '-')    # long dash
        s = s.replace('−',      '-')    # minus sign, yes this is a different character from above
        # s = s.replace('•':      '*')  # bullet
        s = s.replace('\u2019', '"')    # single quote
        s = s.replace('\u2018', '"')    # another single quote
        s = s.replace('\xe6',   'ae')   # ae symbol
        s = s.replace('á',      'a')    # a with accent
        s = s.replace('à',      'a')    # a with accent going the other way
        s = s.replace('â',      'a')    # a with caret
        s = s.replace('é',      'e')    # e with accent
        s = s.replace('í',      'i')    # i with accent
        s = s.replace('ñ',      'u')    # n with tilda
        s = s.replace('ö',      'o')    # o with umlaut
        s = s.replace('û',      'u')    # u with caret
        s = s.replace('ú',      'u')    # u with accent
        s = s.replace('ü',      'u')    # u with umlaut
        s = s.replace('π',      'pi')   # pi
        s = s.replace('®',      'r')    # Registered trademark as r
        # s = s.replace('½',      '1/2')  # 1/2
        # s = s.replace('∞',      'inf')  # infinity
        s = s.replace('\u2610', 'na')   # ballot box as na
        return s

    card['name'] = sub_unicode(card['name'])
    card['type'] = sub_unicode(card['type'])
    if card['main_text'] is not None:
        card['main_text'] = sub_unicode(card['main_text'])
    if card['flavor'] is not None:
        card['flavor'] = sub_unicode(card['flavor'])

    if card['main_text'] is not None:
        # remove ability words, which thematically groups cards with a common functionality, but have no actual rules meaning
        card['main_text'] = re.sub(rf'((?<=\s)|(?<=^))({"|".join(MTG_ABILITY_WORDS)})(\s*\-\s*|\s+)', '', card['main_text'])

        card['main_text'] = XYZ_variable_capitalize(card['main_text'])

        # coerce pipes used in card descriptions to colons
        # pipes were only used for one set, and they were used as colons would be. No other cards have pipes in their text.
        # this reduces vocab and improves consistency for the AI
        card['main_text'] = re.sub(r' *\|', ':', card['main_text'])

        # coerce counters to all lower case, to decrease recognition complexity for the AI
        # there are only two cards in the verse (at time of writing) which have capitalized counter names
        #   One card uses 'Shield counter' at the beginning of a sentence
        #   The other card uses the 'CLANK!' counter
        card['main_text'] = re.sub(rf'(?:{"|".join(MTG_COUNTERS)}) counter', lambda x: x.group(0).lower(), card['main_text'])

        # transform small (<= 20) text encoded numbers into decimal
        #   decimal numbers will be encoded to unary during internal_format_to_AI_format, which is more consistent and extensible for the AI
        #   doing the decimal conversion step here instead of in that function provides a consistent encoder -> decoder loop target
        # eg "choose one " -> "choose 1 "
        # remove the card name temporarily, as a precaution against modifying that
        #   Don't need to worry about modifying any reserved words, since none contain delimited number words
        card['main_text'] = card['main_text'].replace(card['name'], '@')
        num_regex = "|".join(nwc.NUMBER_WORDS)
        regex = fr'(?:(?<=^)|(?<=\W))((?:{num_regex})(?:[ \-](?:{num_regex}|and))*(?:[ \-](?:{num_regex}))?)(?=$|\W)'
        def convert(s):
            s = s.group(1)
            ns = nwc.str_to_int(s)
            if int(ns) <= 20:
                return ns
            else:
                return s  # don't convert large nubmers back to decimal (See above step which converts them to words)
        card['main_text'] = re.sub(regex, convert, card['main_text'])
        card['main_text'] = card['main_text'].replace('@', card['name'])  # replace card name

        # TODO maybe? Might improve regularization
        # text_val = transforms.text_pass_8_equip(text_val)
        #   careful about things like this "Equip Shaman, Warlock, or Wizard {1}"
        # text_val = transforms.text_pass_11_linetrans(text_val)  # standardize order of keywords

        # remove reminder text (eg keyword explanations)
        # TODO this makes a pretty big assumption that that all parentheses are useless, which is hard to verify...
        # TODO this removes some real rules text (not reminder), and all text from some cards (Plains)
        #   '(Activate only as an instant.)'
        #   '(This effect lasts indefinitely.)'
        #   etc
        # card['main_text'] = re.sub(r'(?<!^)\([^\)]*\)', '', card['main_text'])
        for x in MTG_REMINDER_TEXT:
            if x.preface:
                card['main_text'] = re.sub(fr'({x.preface}[^\n\(]*){x.reminder}', r'\1', card['main_text'])
            else:
                card['main_text'] = re.sub(x.reminder, '', card['main_text'])

        # remove trailing whitespace on a line, and remove blank lines, which might for instance by introduced by the above
        # don't remove leading whitespace, which might be intentional formatting
        card['main_text'] = re.sub(r'\s+(?=\n|$)', '', card['main_text'])

        # make field None if it is now empty
        card['main_text'] = card['main_text'] or None

    # TODO correct when only a part of the card name is used in the main_text to refer to the card
    #   eg "1996 World Champion" may be referred to as "World Champion" in the main text
    #   eg "Crovax, Ascendant Hero" may be referred to as "Crovax" in the main text
    #   apostrophes are also difficult, since sometimes its <name>'s in the possessive, but some card names also contain apostrophes ('Urza's Mine')
    # change these to full name references
    # this is difficult to verify...
    # finally, some cards reference only a part of the name field in the main_text, so we handle that by searching for every possible substring
    # check if the found match in the main_text field is a reference to another name by searching for adjacent capitalized words to form the full name
    # check in the next word in both directions is capitalized
    #   Actually the capitalized check is a bit broken because the substring could be a the beginning/end of a sentence
    #       or 2nd word in a sentence, or a reserved word, or ...
    #   then if the full name from the main text is not equal to the substring, its not a match
    #   repeat in both directions until the string doesn't change
    # Note: this code doesn't really work, and it has a pretty middling runtime
    #   it really needs a much more sophisticated parser to determine whether a partial match should be replaced
    #   or whether the partial match refers to a different object or is part of a bigger different name
    #   and sometimes keywords are in the card name, se we gotta determine how to differentiate usage
    #   Therefore its not enabled...
    # mtgencode's implementation isn't great either
    #   breaking on commas in the name makes some incorrect replacements
    #   eg the card 'Icingdeath, Frost Tyrant' references tokens named 'Icingdeath, Frost Tounge'
    # subs = None
    # for i_substring, substring in enumerate(non_trivial_substrings(name)):
    #     if i_substring == 0:
    #         main_text = main_text.replace(substring, '@')
    #         main_text, subs = temporarily_remove_reserved_words(main_text)
    #     if i_substring > 0:
    #         start = 0
    #         while start is not None:
    #             capture = capture_named_context(substring, main_text, start=start)
    #             if capture is None:
    #                 start = None
    #             else:
    #                 capture, start, end = capture
    #                 if capture == substring:  # check if capture added anything
    #                     q = '\''
    #                     print(f'--Found-- \'{capture + q: <20} #{start: <4} (from {name + ")": <50} -> {repr(main_text)}')
    #                 else:
    #                     print(f'--Dropped-- \'{substring}\' # \'{capture}\'', '->', repr(main_text))
    #                     print('\t->', re.split(r'((?:(?<!\w)\-(?!\w)|[^\w@\-\+\/])+)', main_text))
    #                 start = end  # for next loop iteration
    # main_text = replace_temporarily_removed_reserved_words(main_text, subs)

    # apply strict titlecasing to the card name
    # this gives us a robust target for the AI to internal decoder, since the AI text is all lowercase
    # apply the exact same transformation to the card name when found in the main text
    #   since references to card title are encoded to special characters in the AI format, and we need to be able to find them later
    # Since we chose to let the AI handle capitalization, we've disabled this block. It does otherwise work tho.
    # new_name = titlecase.titlecase(card['name'].lower())  # lower() call ensures titlecaser doesn't try to get too smart about acronym capitalization
    # if card['main_text'] is not None:
    #     segments = re.split(fr"({re.escape(card['name'])})", card['main_text'])
    #     segments = list(segments)
    #     for i_segment, segment in enumerate(segments):
    #         if segment == card['name']:
    #             segments[i_segment] = new_name
    #     card['main_text'] = ''.join(segments)
    # card['name'] = new_name

    # recurse on b-e sides
    if 'b_side' in card:
        card['b_side'] = unreversable_modifications(card['b_side'])
    if 'c_side' in card:
        card['c_side'] = unreversable_modifications(card['c_side'])
    if 'd_side' in card:
        card['d_side'] = unreversable_modifications(card['d_side'])
    if 'e_side' in card:
        card['e_side'] = unreversable_modifications(card['e_side'])

    return card


def verify_decoder_reverses_encoder(cards, cards_dual_processed):
    # this helps validate that both the encoder and decorder are working properly, or at least have symmetric bugs
    # consumes two lists of internally formatted cards, and compares them
    # if the two are not equal, raises error
    # this is only executed during encode_json_to_AI
    #   and is a test of the program design over the space of the cards from AllPrintings.json
    #   this does not process any AI generated data

    if cards == cards_dual_processed:
        print('Encoder -> Decoder loop passed verification!')
    else:
        for i_card, card in enumerate(cards):
            card_dp = cards_dual_processed[i_card]
            if card != card_dp:
                print('Encoder -> Decoder loop Failed, printing one card diff for context.')
                print(card['name'])
                card_lines    = pprint.pformat(card).split('\n')
                card_dp_lines = pprint.pformat(card_dp).split('\n')
                diff = difflib.unified_diff(card_lines, card_dp_lines)
                diff = list(diff)
                pprint.pprint(diff)
                sys.exit(1)


def encode_json_to_AI_main(json_path, out_path):
    # consumes AllPrintings.json
    # runs through encoding and decoding steps
    #   comapares encoded+decoded dataset to original dataset for end-to-end validity checking
    # produces several local data files for human comparison / debugging if validation fails
    # saves encoded data file to designated location

    cards = json_to_internal_format(json_path)
    for card in cards:
        validate(card)

    # perform dataset modifications / standardizations which have no reverse
    cards = [unreversable_modifications(card) for card in cards]

    # drop the flavor text, we don't encode it in this function
    #   and we need the field omitted for the encoder -> decoder loop verification
    # do this before deduplication so that this field is not considered
    for card in cards:
        del card['flavor']
        if 'b_side' in card: del card['b_side']['flavor']
        if 'c_side' in card: del card['c_side']['flavor']
        if 'd_side' in card: del card['d_side']['flavor']
        if 'e_side' in card: del card['e_side']['flavor']

    # deduplicate the cards
    # We do this after standardization due to some unfortunate artifacts in the json fields, which are addressed in that step
    cards = deduplicate_cards(cards)

    # TODO remove
    keep = [
        '({T}: Add {G}.)',
        '({T}: Add {B}.)',
        '({T}: Add {U}.)',
        '({T}: Add {R}.)',
        '({T}: Add {W}.)',
        '({T}: Add {R} or {G}.)',
        '({T}: Add {W} or {U}.)',
        '({T}: Add {U} or {B}.)',
        '({T}: Add {B} or {R}.)',
        '({T}: Add {G} or {W}.)',
        '({T}: Add {B} or {G}.)',
        '({T}: Add {G} or {U}.)',
        '({T}: Add {W} or {B}.)',
        '({T}: Add {R} or {W}.)',
        '({T}: Add {U} or {R}.)',
        '({T}: Add {B}, {G}, or {U}.)',
        '({T}: Add {B}, {R}, or {G}.)',
        '({T}: Add {G}, {U}, or {R}.)',
        '({T}: Add {G}, {W}, or {U}.)',
        '({T}: Add {R}, {G}, or {W}.)',
        '({T}: Add {R}, {W}, or {B}.)',
        '({T}: Add {U}, {B}, or {R}.)',
        '({T}: Add {U}, {R}, or {W}.)',
        '({T}: Add {W}, {B}, or {G}.)',
        '({T}: Add {W}, {U}, or {B}.)',
        '(Mana symbols on that permanent remain unchanged.)',
        '(Do this before you draw.)',
        '(Then put Timetwister into its owner\'s graveyard.)',
        '(Your party consists of up to 1 each of Cleric, Rogue, Warrior, and Wizard.)',
        '(Seat of the Synod isn\'t a spell.)',
        '(As this Saga enters and after your draw step, add a lore counter. Sacrifice after I.)',
        '(As this Saga enters and after your draw step, add a lore counter. Sacrifice after II.)',
        '(As this Saga enters and after your draw step, add a lore counter. Sacrifice after III.)',
        '(As this Saga enters and after your draw step, add a lore counter. Sacrifice after IV.)',
        '(As this Saga enters and after your draw step, add a lore counter. Sacrifice after V.)',
        '(As this Saga enters and after your draw step, add a lore counter.)',
        '(Mana abilities can\'t be targeted.)',
        '(Piles can be empty.)',
        '(Gain the next level as a sorcery to add its ability.)',
        '(An ongoing scheme remains face up until it\'s abandoned.)',
        '(Start the game with this conspiracy face up in the command zone.)',
        '(You may cast a legendary sorcery only if you control a legendary creature or planeswalker.)',
        '(Auras with nothing to enchant remain in your graveyard.)',
        '(This spell works on creatures that can\'t be blocked.)',
        '(The votes can be for different choices or for the same choice.)',
        '(It\'s put into its owner\'s junkyard.)',
        '(This effect lasts indefinitely.)',
        '(Return it only if it\'s on the battlefield.)',
        '(Then planeswalk away from this phenomenon.)',
    ]
    import tabulate
    with_context = defaultdict(int)
    without_context = defaultdict(int)
    found_parenthesized = defaultdict(int)
    for card in cards:
        if card['main_text'] is not None:
            s = re.findall(r'(?:(?<=\n)|(?<=^))([^\(\n]*)(\([^\)]*\))', card['main_text'])
            s2 = re.findall(r'\([^\)]*\)', card['main_text'])
            for preface, parenthesized in s:
                if parenthesized not in keep:
                    with_context[preface + parenthesized] += 1
                    found_parenthesized[parenthesized] += 1
            for parenthesized in s2:
                if parenthesized not in found_parenthesized and parenthesized not in keep:
                    without_context[parenthesized] += 1
    with_context = [[v, k] for k,v in with_context.items()]
    with_context.sort(key = lambda x: [-x[0], x[1]])
    print(tabulate.tabulate(with_context, tablefmt='pipe'))
    without_context = [[v, k] for k,v in without_context.items()]
    without_context.sort(key = lambda x: [-x[0], x[1]])
    print(tabulate.tabulate(without_context, tablefmt='pipe'))
    found_parenthesized = [[v, k] for k,v in found_parenthesized.items()]
    found_parenthesized.sort(key = lambda x: [-x[0], x[1]])
    print(tabulate.tabulate(found_parenthesized, tablefmt='pipe'))
    sys.exit()

    # limit dataset to those cards upon which the AI should train
    cards = limit_to_AI_training_cards(cards)

    # transcribe to AI format, and save in designated location
    cards_AI = [internal_format_to_AI_format(card) for card in cards]
    f = open(out_path, 'w')
    f.write('\n'.join(cards_AI))
    f.close()

    # decode AI format back to internal format, and then compare to the limited dataset from above
    cards_dual_processed = [AI_to_internal_format(card) for card in cards_AI]
    verify_decoder_reverses_encoder(cards, cards_dual_processed)


def encode_json_to_AI_flavor(json_path, out_path):
    pass  # TODO


def encode_json_to_AI_names(json_path, out_path):
    pass  # TODO


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--json_path", type=str, help="path to names AllPrintings.json")
    parser.add_argument("--out_path", type=str, help="path to output file")
    args = parser.parse_args()

    encode_json_to_AI_main(args.json_path, args.out_path)

