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


def XYZ_variable_capitalize(s):
    # Capitalize all X's, Y's, and Z's, when acting as variables
    variable_x_regex = r'((?<=^)|(?<=[\s\+\-\/\{]))([xXyYzZ])(?=$|[\s:,\.\/\}])'
    capitalize = lambda x: x.group(2).upper()
    return re.sub(variable_x_regex, capitalize, s)


def deduplicate_cards(cards):
    # consumes list of internal formats, returns list of internal formats
    # drops identical copies of cards
    # TODO if the only difference between cards is rarity, chooses only one of those copies

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
            if card not in unique_group:
                unique_group.append(card)
        unique_cards.extend(unique_group)

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
    # TODO

    # convert fields to local variables, specifically do not edit input dict
    # add default values for AI fields when card fields are None
    cost            = card['cost'] or ''
    loyalty         = card['loyalty'] or ''
    main_text       = card['main_text'] or ''
    type_string     = card['type']
    name            = card['name']
    power_toughness = card['power_toughness'] or []
    rarity          = card['rarity']

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

    # text_val = transforms.text_pass_7_choice(text_val)

    # label fields for the AI
    #   this increases syntax, but regularizes AI output, so is a net win
    AI_string = f'{name}|1{cost}|2{type_string}|3{loyalty}|4{power_toughness}|5{rarity}|6{main_text}'

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
    # TODO

    AI_string = error_correct_AI(AI_string)

    sides = AI_string.split('␥')
    assert sides

    # breakup fields
    card = {}
    fields = re.split(r'(\|\d)', sides[0])
    card['name'] = fields[0]

    field_names = {'|1': 'cost', '|2': 'type', '|3': 'loyalty', '|4': 'power_toughness', '|5': 'rarity', '|6': 'main_text'}
    for field_id, field in pairs(fields[1:]):
        field_name = field_names[field_id]
        card[field_name] = field

    for k, v in field_names.items():
        assert v in card, f'Failed to find field "{v}" in "{AI_string}" -> {fields}'

    # decode newlines
    card['main_text'] = card['main_text'].replace('\\', '\n')

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
    card['loyalty'] = re.sub(r'⓪(\^*)', lambda x: unary_to_decimal(x.group(1)), card['loyalty'])
    card['main_text'] = re.sub(r'⓪(\^*)', lambda x: unary_to_decimal(x.group(1)), card['main_text'])
    card['power_toughness'] = re.sub(r'⓪(\^*)', lambda x: unary_to_decimal(x.group(1)), card['power_toughness'])

    # reduce character overloading for dashes
    # convert numerical minus signs to a unique character
    card['main_text'] = re.sub(r'∓', '-', card['main_text'])

    # decode power toughness
    if card['power_toughness'] != '':
        card['power_toughness'] = card['power_toughness'].split('/')

    # TODO replace backreferences to name
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
    # TODO also substitute pipes used as colons...

    # strip text fields
    card['name'] = card['name'].strip()
    if card['main_text'] is not None:
        card['main_text'] = card['main_text'].strip()
    if card['flavor'] is not None:
        card['flavor'] = card['flavor'].strip()

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
        # remove rules (keyword explanation) text
        # TODO this makes a pretty big assumption that that all parentheses are useless, which is hard to verify...
        # TODO this deletes all text from the card named "Plains"
        card['main_text'] = re.sub(r'(?<!^)\([^\)]*\)', '', card['main_text'])

        # remove ability words, which thematically groups cards with a common functionality, but have no actual rules meaning
        card['main_text'] = re.sub(rf'((?<=\s)|(?<=^))({"|".join(MTG_ABILITY_WORDS)})(\s*\-\s*|\s+)', '', card['main_text'])

        card['main_text'] = XYZ_variable_capitalize(card['main_text'])

        # coerce counters to all lower case, to decrease recognition complexity for the AI
        # there are only two cards in the verse (at time of writing) which have capitalized counter names
        #   One card uses 'Shield counter' at the beginning of a sentence
        #   The other card uses the 'CLANK!' counter
        card['main_text'] = re.sub(rf'(?:{"|".join(MTG_COUNTERS)}) counter', lambda x: x.group(0).lower(), card['main_text'])

        # TODO
        # transform text smaller encoded numbers into decimal
        #   decimal numbers will be encoded to unary during internal_format_to_AI_format, which is more consistent and extensible for the AI
        #   doing the decimal conversion step here instead of in that function provides a consistent encoder -> decoder loop target
        # eg "choose one " -> "choose 1 "
        # first, remove the card name temporarily, as a precaution against modifying that
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

