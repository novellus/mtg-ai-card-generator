# constants describing mtg card attributes. These may need to be updated whenever new mechanics are released.


import titlecase
import re

from collections import defaultdict
from collections import namedtuple


def extend_all_cases(l):
    # extends a list l with all reasonable cases for its original contents
    new = []
    new.extend([titlecase.titlecase(x) for x in l])
    new.extend([x.capitalize() for x in l])
    new.extend([x.upper() for x in l])
    new.extend([x.lower() for x in l])
    return list(set(new + l))


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

def mtg_mana_symbol_valid(s):
    if s in MTG_SYMBOL_JSON_TO_AI_FORMAT:
        return True
    elif re.search(r'\{\d+\}', s):
        return True
    return False


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
    rm(fr'',                                                  r"(?:\d+ |an )?energy counters?"),
    rm(fr'',                                                  r"(?:\d+ |a )?ticket counters?"),
    rm(fr'',                                                  r"(?:This creature|This|It|You|They) can't attack, and it can block creatures with flying"),
    rm(fr'',                                                  r"(?:To assemble a Contraption, p|P)ut the top card of your Contraption deck face up onto 1 of your sprockets(?:\. Then repeat this process)?"),
    rm(fr'',                                                  r"\{2/[A-Z]\} can be paid with any 2 mana or with[^\)]*"),
    rm(fr'',                                                  r"\{[A-Z]/P\} can be paid with either \{[A-Z]\} or 2 life"),
    rm(fr'',                                                  r"\{[A-Z]\/[A-Z]\} can be paid with either \{[A-Z]\} or \{[A-Z]\}"),
    rm(fr'',                                                  r"\{C\} represents colorless mana"),
    rm(fr'',                                                  r"\{Q\} is the untap symbol"),
    rm(fr'',                                                  r"\{S\} can be paid with 1 mana from a snow source"),
    rm(fr'',                                                  r"\{S\} is mana from a snow source"),
    rm(fr'',                                                  r"A copy of a permanent spell becomes a token"),
    rm(fr'',                                                  r"Mana cost includes color"),
    rm(fr'',                                                  r"A copy of an Aura spell becomes a token."),
    rm(fr'',                                                  r"A creature with defender can't attack"),
    rm(fr'',                                                  r"A creature with hexproof can't be the target of spells or abilities your opponents control"),
    rm(fr'',                                                  r"A creature with intimidate can't be blocked except by artifact creatures and\/or creatures that share a color with it"),
    rm(fr'',                                                  r"A creature with menace can't be blocked except by 2 or more creatures"),
    rm(fr'',                                                  r"A Food token is an artifact with \"\{2\}, \{T\}, Sacrifice this artifact: You gain 3 life.?\""),
    rm(fr'',                                                  r"A Gold token is an artifact with \"Sacrifice this artifact: Add 1 mana of any color.?\""),
    rm(fr'',                                                  r"A Treasure token is an artifact with \"\{T\}, Sacrifice this artifact: Add 1 mana of any color.?\""),
    rm(fr'',                                                  r"Any amount of damage a creature with deathtouch deals to a creature is enough to destroy it"),
    rm(fr'',                                                  r"Artifact, creature, enchantment, instant, land, planeswalker, sorcery, and tribal are card types"),
    rm(fr'',                                                  r"Artifacts, legendaries, and Sagas are historic"),
    rm(fr'',                                                  r"Damage causes loss of life"),
    rm(fr'',                                                  r"Damage dealt by a creature with lifelink also causes its controller to gain that much life"),
    rm(fr'',                                                  r"Equipment, Auras you control, and counters are modifications"),
    rm(fr'',                                                  r"For example[^\)]*"),
    rm(fr'',                                                  r"It doesn't need to have gone on the adventure first"),
    rm(fr'',                                                  r"Target a land as you cast this. This card enters the battlefield attached to that land"),
    rm(fr'',                                                  r"That creature returns under its owner's control"),
    rm(fr'',                                                  r"The vowels are A, E, I, O, U, and Y"),
    rm(fr'',                                                  r"To have a creature connive, draw a card, then discard a card. If you discarded a nonland card, put a \+1\/\+1 counter on that creature"),
    rm(fr'',                                                  r"To investigate, create a Clue token. It's an artifact with \"\{2\}, Sacrifice this artifact: Draw a card\.?\""),
    rm(fr'',                                                  r"To mill a card, put the top card of your library into your graveyard"),
    rm(fr'',                                                  r"Zero is even"),
    rm(fr'[Aa]dapt',                                          fr"If this creature has no \+1\/\+1 counters on it, put (?:a|\d+) \+1\/\+1 counters? on it"),
    rm(fr'[Aa]ffinity for \w+',                               r"(?:This|It|You|They) spell costs \{1\} less to cast for each [\w ]+ you control"),
    rm(fr'[Aa]fflict',                                        fr"Whenever this creature becomes blocked, defending player loses \d+ life"),
    rm(fr'[Aa]fterlife',                                      fr"When this creature dies, create (?:\d+|a) 1\/1 white and black Spirit creature tokens? with flying"),
    rm(fr'[Aa]mass',                                          fr"Put (?:\d+|a) \+1\/\+1 counters? on an Army you control. If you don't control 1, create a 0\/0 black Zombie Army creature token first"),
    rm(fr'[Aa]mplify',                                        fr"As this creature enters the battlefield, put (?:\d+|a) \+1\/\+1 counters? on it for each (\w+) card you reveal in your hand"),
    rm(fr'[Aa]nnihilator',                                    r"Whenever this creature attacks, defending player sacrifices (?:a|\d+) permanents?"),
    rm(fr'[Aa]scend',                                         r"If you control 10 or more permanents, you get the city's blessing for the rest of the game"),
    rm(fr'[Aa]ssist',                                         fr"Another player can pay up to (?:{MTG_SYMBOL_REGEX})+ of this spell's cost(?:\. You choose the value of X)?"),
    rm(fr'[Aa]ugment',                                        fr"(?:{MTG_SYMBOL_REGEX})+, Reveal this card from your hand: Combine it with target host. Augment only as a sorcery"),
    rm(fr'[Aa]waken',                                         fr"If you cast this spell for (?:{MTG_SYMBOL_REGEX})+, also put \d+ \+1\/\+1 counters on target land you control and it becomes a 0/0 Elemental creature with haste. It's still a land"),
    rm(fr'[Bb]ands with other legendary creatures',           fr"Any legendary creatures can attack in a band as long as at least 1 has \"bands with other legendary creatures.\" Bands are blocked as a group. If at least 2 legendary creatures you control, 1 of which has \"?bands with other legendary creatures,\"? are blocking or being blocked by the same creature, you divide that creature's combat damage, not its controller, among any of the creatures it's being blocked by or is blocking"),
    rm(fr'[Bb]anding',                                        fr"Any creatures with banding, and up to 1 without, can attack in a band. Bands are blocked as a group. If any creatures with banding (?:a player|you) controls? are blocking or being blocked by a creature, (?:you|that player) divides? that creature's combat damage, not its controller, among any of the creatures it's being blocked by or is blocking"),
    rm(fr'[Bb]asic landcycling',                              fr"(?:{MTG_SYMBOL_REGEX})+, Discard this card: Search your library for a basic land card, reveal it, put it into your hand, then shuffle"),
    rm(fr'[Bb]attle cry',                                     r"Whenever this creature attacks, each other attacking creature gets \+1\/\+0 until end of turn"),
    rm(fr'[Bb]estow',                                         fr"If you cast this card for its bestow cost, it's an Aura spell with enchant creature. It becomes a creature again if it's not attached to a creature"),
    rm(fr'[Bb]litz',                                          fr"If you cast this spell for its blitz cost, it gains haste and \"When this creature dies, draw a card.\" Sacrifice it at the beginning of the next end step"),
    rm(fr'[Bb]lood token',                                    r"(?:They're|It's an) artifacts? with \"\{1\}, \{T\}, Discard a card, Sacrifice this artifact: Draw a card\.?\""),
    rm(fr'[Bb]loodthirst',                                    r"If an opponent was dealt damage this turn, this creature enters the battlefield with (?:a|\d+) \+1\/\+1 counters? on it"),
    rm(fr'[Bb]oast',                                          fr"Activate only if this creature attacked this turn and only once each turn"),
    rm(fr'[Bb]olster',                                        fr"Choose a creature with the least toughness among creatures you control and put (?:a|\d|X) \+1/\+1 counters? on it"),
    rm(fr'[Bb]ushido',                                        r"Whenever this creature blocks or becomes blocked, it gets \+\d+\/\+\d+ until end of turn"),
    rm(fr'[Bb]uyback',                                        fr"You may (?:(?:sacrifice a land|discard \d+ cards) in addition to any other costs|pay an additional (?:{MTG_SYMBOL_REGEX})+) as you cast this spell. If you do, put this card into your hand as it resolves"),
    rm(fr'[Cc]ascade',                                        r"When you cast this spell, exile cards from the top of your library until you exile a nonland card that costs less. You may cast it without paying its mana cost. Put the exiled cards on the bottom of your library in a random order"),
    rm(fr'[Cc]asualty',                                       fr"As you cast this spell, you may sacrifice a creature with power \d+ or greater. When you do, copy this spell(?: and you may choose a new target for the copy)?"),
    rm(fr'[Cc]hampion an? \w+',                               fr"When this enters the battlefield, sacrifice it unless you exile another \w+ you control. When this leaves the battlefield, that card returns to the battlefield"),
    rm(fr'[Cc]hangeling',                                     r"(?:This card|It|You) is every creature type"),
    rm(fr'[Cc]hoose a [Bb]ackground',                         r"You can have a Background as a second commander"),
    rm(fr'[Cc]ipher',                                         r"Then you may exile this spell card encoded on a creature you control. Whenever that creature deals combat damage to a player, its controller may cast a copy of the encoded card without paying its mana cost"),
    rm(fr'[Cc]lash',                                          r"Each clashing player reveals the top card of their library, then puts that card on the top or bottom. A player wins if their card had a higher mana value"),
    rm(fr'[Cc]leave',                                         r"You may cast this spell for its cleave cost. If you do, remove the words in square brackets"),
    rm(fr'[Cc]ompanion',                                      r"If this card is your chosen companion, you may put it into your hand from outside the game for \{3\} any time you could cast a sorcery"),
    rm(fr'[Cc]onnive',                                        r"(?:Its controller d|D)raws? (?:a|X) cards?, then discard (?:a|X) cards?. (?:If (?:they|you) discarded a nonland card,(?: they)? p|P)ut a \+1\/\+1 counter on (that|this) creature(?: for each nonland card discarded this way)?"),
    rm(fr'[Cc]onspire',                                       fr"As you cast this spell, you may tap 2 untapped creatures you control that share a color with it. When you do, copy it(?: and you may choose a new target for the copy)?"),
    rm(fr'[Cc]onvoke',                                        r"Your creatures can help cast this spell. Each creature you tap while casting this spell pays for \{1\} or 1 mana of that creature's color"),
    rm(fr'[Cc]rew',                                           r"Tap any number of creatures you control with total power \d+ or more: This Vehicle becomes an artifact creature until end of turn"),
    rm(fr'[Cc]umulative upkeep',                              r"At the beginning of (?:its controller's|your) upkeep,(?: that player)? puts? an age counter on (?:it|this permanent), then sacrifices? it unless (?:you|they) pay its upkeep cost for each age counter on it(?:\. \{\S} can be paid with 1 mana from a snow source)?"),
    rm(fr'[Cc]ycling',                                        fr"(?:-Sacrifice a land|Pay \d+ life|(?:{MTG_SYMBOL_REGEX})+), Discard this card: Draw a card"),
    rm(fr'[Dd]ash',                                           fr"You may cast this spell for its dash cost. If you do, it gains haste, and it's returned from the battlefield to its owner's hand at the beginning of the next end step"),
    rm(fr'[Dd]aybound',                                       r"If a player casts no spells during their own turn, it becomes night next turn"),
    rm(fr'[Dd]eathtouch',                                     r"Any amount of damage (?:this|that|it|they|you) deals? to a creature is enough to destroy (?:that creature|it)"),
    rm(fr'[Dd]ecayed',                                        r"(A creature with decayed|It) can't block. When it attacks, sacrifice it at end of combat"),
    rm(fr'[Dd]efender',                                       r"(?:This creature|This|It|You|They) can't attack"),
    rm(fr'[Dd]elve',                                          r"Each card you exile from your graveyard while casting this spell pays for \{1\}"),
    rm(fr'[Dd]emonstrate',                                    r"When you cast this spell, you may copy it. If you do, choose an opponent to also copy it(?:\. Players may choose new targets for their copies)?"),
    rm(fr'[Dd]estroy target Attractio',                       r"It's put into its owner's junkyard"),
    rm(fr'[Dd]etain',                                         r"Until your next turn, (?:those|that) (?:permanent|creature)s? can't attack or block and (?:their|its) activated abilities can't be activated"),
    rm(fr'[Dd]ethrone',                                       r"Whenever this creature attacks the player with the most life or tied for most life, put a \+1\/\+1 counter on it"),
    rm(fr'[Dd]evoid',                                         r"(?:This creature|This card|It|You|They) has no color"),
    rm(fr'[Dd]evotion to (?:black|white|blue|green|red)',     fr"Each (?:{MTG_SYMBOL_REGEX})+ in the mana costs of permanents you control counts toward your devotion to (?:black|white|blue|green|red)"),
    rm(fr'[Dd]evour',                                         r"As this enters the battlefield, you may sacrifice any number of creatures. This creature enters the battlefield with(?: twice| \d+ times)? that many \+\d+\/\+\d+ counters on it"),
    rm(fr'[Dd]isturb',                                        r"You may cast this card from your graveyard transformed for its disturb cost"),
    rm(fr'[Dd]ouble strike',                                  r"(?:This creature|This|It|You|They) deals? both first-strike and regular combat damage"),
    rm(fr'[Dd]redge',                                         r"If you would draw a card, you may mill (?:a|\d+) cards? instead. If you do, return this card from your graveyard to your hand"),
    rm(fr'[Ee]cho',                                           fr"At the beginning of your upkeep, if this came under your control since the beginning of your last upkeep, sacrifice it unless you pay its echo cost"),
    rm(fr'[Ee]mbalm',                                         fr"(?:{MTG_SYMBOL_REGEX})+, Exile this card from your graveyard: Create a token that's a copy of it, except it's a white Zombie [\w ]+ with no mana cost. Embalm only as a sorcery"),
    rm(fr'[Ee]merge',                                         fr"You may cast this spell by sacrificing a creature and paying the emerge cost reduced by that creature's mana value"),
    rm(fr'[Ee]nchant creature',                               r"Target a creature as you cast this. This card enters the battlefield attached to that creature"),
    rm(fr'[Ee]ncore',                                         fr"(?:{MTG_SYMBOL_REGEX})+, Exile this card from your graveyard: For each opponent, create a token copy that attacks that opponent this turn if able. They gain haste. Sacrifice them at the beginning of the next end step. Activate only as a sorcery"),
    rm(fr'[Ee]nd the turn',                                   r"Exile all spells and abilities from the stack, including this card. The player whose turn it is discards down to their maximum hand size. Damage wears off, and \"this turn\" and \"until end of turn\" effects end"),
    rm(fr'[Ee]nd the turn',                                   r"Exile all spells and abilities from the stack. Discard down to your maximum hand size. Damage wears off, and \"this turn\" and \"until end of turn\" effects end"),
    rm(fr'[Ee]nlist',                                         fr"As this creature attacks, you may tap a nonattacking creature you control without summoning sickness. When you do, add its power to this creature's until end of turn"),
    rm(fr'[Ee]ntwine',                                        fr"Choose both if you pay the entwine cost"),
    rm(fr'[Ee]pic',                                           r"For the rest of the game, you can't cast spells. At the beginning of each of your upkeeps, copy this spell except for its epic ability(?:\. You may choose a new target for the copy)?"),
    rm(fr'[Ee]quip',                                          fr"(?:{MTG_SYMBOL_REGEX})+: Attach to target creature you control. Equip only as a sorcery(?:\. This card enters the battlefield unattached and stays on the battlefield if the creature leaves)?"),
    rm(fr'[Ee]scalate',                                       r"Pay this cost for each mode chosen beyond the first"),
    rm(fr'[Ee]scape',                                         r"You may cast this card from your graveyard for its escape cost"),
    rm(fr'[Ee]ternalize',                                     fr"(?:{MTG_SYMBOL_REGEX})+, Exile this card from your graveyard: Create a token that's a copy of it, except it's a 4/4 black Zombie [\w ]+ with no mana cost. Eternalize only as a sorcery"),
    rm(fr'[Ee]voke',                                          r"You may cast this spell for its evoke cost. If you do, it's sacrificed when it enters the battlefield"),
    rm(fr'[Ee]volve',                                         r"Whenever a creature enters the battlefield under your control, if that creature has greater power or toughness than this creature, put a \+1\/\+1 counter on this creature"),
    rm(fr'[Ee]xalted',                                        r"Whenever a creature(?: you control)? attacks alone, (?:it|that creature) gets \+1\/\+1 until end of turn(?: for each instance of exalted among permanents (?:you|its controller) controls?)?"),
    rm(fr'[Ee]xert',                                          r"(?:An exerted creature|It) won't untap during your next untap step"),
    rm(fr'[Ee]xploit',                                        r"When this creature enters the battlefield, you may sacrifice a creature"),
    rm(fr'[Ee]xplore',                                        r"Reveal the top card of your library. Put that card into your hand if it's a land. Otherwise, put a \+1\/\+1 counter on (?:the|this) creature, then put the card back or put it into your graveyard"),
    rm(fr'[Ee]xtort',                                         r"Whenever you cast a spell, you may pay {W\/B}. If you do, each opponent loses 1 life and you gain that much life"),
    rm(fr'[Ff]abricate',                                      r"When this creature enters the battlefield, put (?:a|\d+) \+1\/\+1 counters? on it or create (?:a|\d+) 1\/1 colorless Servo artifact creature tokens?"),
    rm(fr'[Ff]ading',                                         fr"(?:This \w+|This|It|You|They) enters the battlefield with \d+ fade counters on it. At the beginning of your upkeep, remove a fade counter from it. If you can't, sacrifice it"),
    rm(fr'[Ff]ear',                                           r"(?:This creature|This|It|You|They) can't be blocked except by artifact creatures and/or black creatures"),
    rm(fr'[Ff]ight',                                          r"Each deals damage equal to its power to the other"),
    rm(fr'[Ff]irst strike',                                   r"(?:This creature|This|It|You|They) deals? combat damage before creatures without first strike"),
    rm(fr'[Ff]lanking',                                       r"Whenever a creature without flanking blocks (?:this creature|[\w ]+), the blocking creature gets \-1\/\-1 until end of turn"),
    rm(fr'[Ff]lash',                                          r"You may cast (it|this spell) any time you could cast an instant"),
    rm(fr'[Ff]lashback',                                      r"You may cast this card from your graveyard for its flashback cost(?: and any additional costs)?. Then exile it"),
    rm(fr'[Ff]lying',                                         r"(?:This creature|This|It|You|They)(?: creature)? can't be blocked except by creatures with flying or reach"),
    rm(fr'[Ff]ood token',                                     r"(It's|They're)(?: an)? artifacts? with \"\{2\}, \{T\}, Sacrifice this artifact: You gain 3 life\.?\""),
    rm(fr'[Ff]orecast',                                       r"Activate only during your upkeep and only once each turn"),
    rm(fr'[Ff]orestcycling',                                  fr"(?:{MTG_SYMBOL_REGEX})+, Discard this card: Search your library for a Forest card, reveal it, put it into your hand, then shuffle"),
    rm(fr'[Ff]orestwalk',                                     r"(?:They|It|You|This creature) can't be blocked as long as defending player controls a Forest"),
    rm(fr'[Ff]oretell',                                       r"During your turn, you may pay \{2\} and exile this card from your hand face down. Cast it on a later turn for its foretell cost"),
    rm(fr'[Ff]riends forever',                                fr"You can have 2 commanders if both have friends forever"),
    rm(fr'[Ff]use',                                           r"You may cast 1 or both halves of this card from your hand"),
    rm(fr'[Gg]old token',                                     r"It's an artifact with \"Sacrifice this artifact: Add 1 mana of any color\.?\""),
    rm(fr'[Gg]oad',                                           r"(?:Until your next turn, )?(?:this creature|that creature|those creatures|this|it|you|[Tt]hey) attacks? each combat if able and attacks? a player other than you if able"),
    rm(fr'[Gg]oad(?:ed)?',                                    r"(?:This creature|That creature|This|It|You|They) attacks each combat if able and attacks a player other than you if able"),
    rm(fr'[Gg]raft',                                          fr"This creature enters the battlefield with \d+ \+1\/\+1 counters on it. Whenever another creature enters the battlefield, you may move a \+1\/\+1 counter from this creature onto it"),
    rm(fr'[Hh]aste',                                          r"(?:This creature|This|It|You|They) can attack and \{T\} this turn"),
    rm(fr'[Hh]aste',                                          r"(?:This creature|This|It|You|They) can attack and \{T\} as soon as (?:they|it) comes? under your control"),
    rm(fr'[Hh]aunt',                                          fr"(?:When this creature dies|When this spell card is put into a graveyard after resolving), exile it haunting target creature"),
    rm(fr'[Hh]exproof',                                       r"(?:This creature|This|It|You|They) can't be the targets? of spells or abilities your opponents control"),
    rm(fr'[Hh]idden agenda',                                  r"Start the game with this conspiracy face down in the command zone and secretly choose a card name. You may turn this conspiracy face up any time and reveal that name"),
    rm(fr'[Hh]ideaway',                                       r"When this (?:land|enchantment) enters the battlefield, look at the top \d+ cards of your library, exile 1 face down, then put the rest on the bottom in a random order"),
    rm(fr'[Hh]orsemanship',                                   r"(?:This creature|This|It|You|They) can't be blocked except by creatures with horsemanship"),
    rm(fr'[Ii]mprovise',                                      r"Your artifacts can help cast this spell. Each artifact you tap after you're done activating mana abilities pays for \{1\}"),
    rm(fr'[Ii]ndestructible',                                 fr"(?:Damage and e|E)ffects that say \"destroy\" don't destroy (?:it|this|them|you)(?: (?:creature|artifact))?(?:\. If its toughness is 0 or less, it's still put into its owner's graveyard)?"),
    rm(fr'[Ii]nfect',                                         r"(?:This creature|This|It|You|They) deals damage to creatures in the form of \-1\/\-1 counters and to players in the form of poison counters"),
    rm(fr'[Ii]ngest',                                         r"Whenever this creature deals combat damage to a player, that player exiles the top card of their library"),
    rm(fr'[Ii]ntimidate',                                     r"(?:This creature|This|It|You|They) can't be blocked except by artifact creatures and\/or creatures that share a color with it"),
    rm(fr'[Ii]nvestigate',                                    fr"Create a(?: colorless)? Clue(?: artifact)? token(?:. It's an artifact)? with \"(?:{MTG_SYMBOL_REGEX})+, Sacrifice this artifact: Draw a card\.?\""),
    rm(fr'[Ii]slandcycling',                                  fr"(?:{MTG_SYMBOL_REGEX})+, Discard this card: Search your library for a Island card, reveal it, put it into your hand, then shuffle"),
    rm(fr'[Ii]slandwalk',                                     r"(?:They|It|You|This creature) can't be blocked as long as defending player controls an Island"),
    rm(fr'[Jj]ump-start',                                     r"You may cast this card from your graveyard by discarding a card in addition to paying its other costs. Then exile this card"),
    rm(fr'[Kk]icker',                                         fr"You may (?:sacrifice (?:a|\d+) \w+s? in addition to any other costs|pay an additional (?:{MTG_SYMBOL_REGEX})+(?: and\/or (?:{MTG_SYMBOL_REGEX})+)?) as you cast this spell"),
    rm(fr'[Ll]andwalk',                                       r"It can't be blocked as long as defending player controls a land of that type"),
    rm(fr'[Ll]ast strike',                                    r"This creature deals combat damage after creatures without last strike"),
    rm(fr'[Ll]earn',                                          r"You may reveal a Lesson card you own from outside the game and put it into your hand, or discard a card to draw a card"),
    rm(fr'[Ll]evel up',                                       fr"(?:{MTG_SYMBOL_REGEX})+: Put a level counter on this. Level up only as a sorcery"),
    rm(fr'[Ll]ifelink',                                       r"Damage dealt by (the|this) creature also causes (?:its controller|you) to gain that much life"),
    rm(fr'[Ll]iving weapon',                                  r"When this Equipment enters the battlefield, create a 0\/0 black Phyrexian Germ creature token, then attach this to it"),
    rm(fr'[Mm]adness',                                        r"If you discard this card, discard it into exile. When you do, cast it for its madness cost or put it into your graveyard"),
    rm(fr'[Mm]anifest',                                       r"Put (?:that card|it) onto the battlefield face down as a 2/2 creature. Turn it face up any time for its mana cost if it's a creature card"),
    rm(fr'[Mm]anifest',                                       r"To manifest a card, put it onto the battlefield face down as a 2\/2 creature. Turn it face up any time for its mana cost if it's a creature card"),
    rm(fr'[Mm]egamorph',                                      fr"You may cast this card face down as a 2\/2 creature for (?:{MTG_SYMBOL_REGEX})+. Turn it face up any time for its megamorph cost and put a \+1\/\+1 counter on it"),
    rm(fr'[Mm]elee',                                          r"Whenever this creature attacks, it gets \+\d+\/\+\d+ until end of turn for each opponent you attacked this combat"),
    rm(fr'[Mm]enace',                                         r"(?:This creature|This|It|You|They) can't be blocked except by 2 or more creatures"),
    rm(fr'[Mm]entor',                                         r"Whenever this creature attacks, put a \+1\/\+1 counter on target attacking creature with lesser power"),
    rm(fr'[Mm]ill',                                           fr"(?:To mill a card, a player puts|You may put|They put|Put) the top(?: \d+)? cards? of (?:their|your) library into (?:their|your) graveyard"),
    rm(fr'[Mm]iracle',                                        fr"You may cast this card for its miracle cost when you draw it if it's the first card you drew this turn"),
    rm(fr'[Mm]odular',                                        fr"(?:This creature|This|It|You|They) enters? the battlefield with (?:a|\d+) \+1\/\+1 counters? on it. When it dies, you may put its \+1\/\+1 counters on target artifact creature"),
    rm(fr'[Mm]onstrosity',                                    r"If this creature isn't monstrous, put (?:a|X|\d+) \+1\/\+1 counters? on it and it becomes monstrous"),
    rm(fr'[Mm]ore Than Meets the Eye',                        r"You may cast this card converted for (?:{MTG_SYMBOL_REGEX})+"),
    rm(fr'[Mm]orph',                                          fr"You may cast this card face down as a 2\/2 creature for (?:{MTG_SYMBOL_REGEX})+. Turn it face up any time for its morph cost"),
    rm(fr'[Mm]ountaincycling',                                fr"(?:{MTG_SYMBOL_REGEX})+, Discard this card: Search your library for a Mountain card, reveal it, put it into your hand, then shuffle"),
    rm(fr'[Mm]ountainwalk',                                   r"(?:They|It|You|This creature) can't be blocked as long as defending player controls a Mountain"),
    rm(fr'[Mm]ultikicker',                                    fr"You may pay an additional (?:{MTG_SYMBOL_REGEX})+ any number of times as you cast this spell"),
    rm(fr'[Mm]utate',                                         fr"If you cast this spell for its mutate cost, put it over or under target non-\w+ creature you own. They mutate into the creature on top plus all abilities from under it"),
    rm(fr'[Mm]yriad',                                         r"Whenever (?:it|this creature) attacks, for each opponent other than defending player, you may create a token that's a copy of (?:that|this) creature that's tapped and attacking that player or a planeswalker they control. Exile the tokens at end of combat"),
    rm(fr'[Nn]injutsu',                                       fr"(?:{MTG_SYMBOL_REGEX})+, Return an unblocked attacker you control to hand: Put this card onto the battlefield from your hand tapped and attacking"),
    rm(fr'[Oo]pen an Attraction',                             r"Put the top card of your Attraction deck onto the battlefield"),
    rm(fr'[Oo]utlast',                                        fr"(?:{MTG_SYMBOL_REGEX})+, "r"\{T\}"fr": Put a \+1\/\+1 counter on this creature. Outlast only as a sorcery"),
    rm(fr'[Oo]verload',                                       fr"You may cast this spell for its overload cost. If you do, change its text by replacing all instances of \"target\" with \"each\.?\""),
    rm(fr'[Pp]artner with',                                   r"When this creature enters the battlefield, target player may put [\w ]+ into their hand from their library, then shuffle"),
    rm(fr'[Pp]artner',                                        r"You can have 2 commanders if both have partner"),
    rm(fr'[Pp]ersist',                                        r"When (?:it|this creature) dies, if it had no \-1\/\-1 counters on it, return it to the battlefield under its owner's control with a \-1\/\-1 counter on it"),
    rm(fr'[Pp]hasing',                                        r"(?:This creature|This|It|You|They) phases in or out before you untap during each of your untap steps. While it's phased out, it's treated as though it doesn't exist"),
    rm(fr'[Pp]lainscycling',                                  fr"(?:{MTG_SYMBOL_REGEX})+, Discard this card: Search your library for a Plains card, reveal it, put it into your hand, then shuffle"),
    rm(fr'[Pp]lainswalk',                                     r"(?:They|It|You|This creature) can't be blocked as long as defending player controls a Plains"),
    rm(fr'[Pp]oison',                                         r"(?:Whenever it deals combat damage to a player, that player gets \d poison counters. )?A player with 10 or more poison counters loses the game"),
    rm(fr'[Pp]opulate',                                       r"(?:To populate, c|C)reate a token that's a copy of a creature token you control(?:\. Do this (?:\d+|X) times)?"),
    rm(fr'[Pp]roliferate',                                    r"Choose any number of permanents and/or players, then give each another counter of each kind already there"),
    rm(fr'[Pp]rotection from (?:black|white|blue|green|red)', r"(?:This creature|This|It|You|They) can't be blocked, targeted, dealt damage, (?:enchanted, or equipped|or enchanted) by anything (?: |or|and|,|(?:black|white|blue|green|red))+"),
    rm(fr'[Pp]rovoke',                                        r"Whenever this creature attacks, you may have target creature defending player controls untap and block it if able"),
    rm(fr'[Pp]rowess',                                        r"Whenever you cast a noncreature spell, this creature gets \+1\/\+1 until end of turn"),
    rm(fr'[Pp]rowl',                                          r"You may cast this for its prowl cost if you dealt combat damage to a player this turn with a \w+(?: or \w+)?"),
    rm(fr'[Rr]ampage',                                        fr"Whenever this creature becomes blocked, it gets \+\d+\/\+\d+ until end of turn for each creature blocking it beyond the first"),
    rm(fr'[Rr]avenous',                                       r"(?:This creature|This|It|You|They) enters? the battlefield with X \+1\/\+1 counters on it. If X is 5 or more, draw a card when it enters\."),  # consider leaving this one in place due to using X, to  teach the AI that X needs a definion
    rm(fr'[Rr]each',                                          r"(?:This creature|This|It|You|They) can block creatures with flying"),
    rm(fr'[Rr]ead ahead',                                     r"Choose a chapter and start with that many lore counters. Add 1 after your draw step. Skipped chapters don't trigger. Sacrifice after III"),
    rm(fr'[Rr]ebound',                                        r"If you cast this spell from your hand, exile it as it resolves. At the beginning of your next upkeep, you may cast this card from exile without paying its mana cost"),
    rm(fr'[Rr]econfigure',                                    fr"(?:{MTG_SYMBOL_REGEX})+: Attach to target creature you control; or unattach from a creature. Reconfigure only as a sorcery. While attached, this isn't a creature"),
    rm(fr'[Rr]egenerate',                                     r"The next time (?:this|that|the) creature would be destroyed this turn, it isn't. Instead tap it, remove all damage from it, and remove it from combat"),
    rm(fr'[Rr]einforce',                                      fr"(?:{MTG_SYMBOL_REGEX})+, Discard this card: Put (?:a|\d+|X) \+1\/\+1 counters? on target creature"),
    rm(fr'[Rr]enown',                                         fr"When this creature deals combat damage to a player, if it isn't renowned, put (?:a|\d+) \+1\/\+1 counters? on it and it becomes renowned"),
    rm(fr'[Rr]eplicate',                                      fr"When you cast this spell, copy it for each time you paid its replicate cost(?:\. You may choose new targets for the copies)?"),
    rm(fr'[Rr]etrace',                                        r"You may cast this card from your graveyard by discarding a land card in addition to paying its other costs"),
    rm(fr'[Rr]iot',                                           r"(?:This creature|This|It|You|They) enters the battlefield with your choice of a \+1\/\+1 counter or haste"),
    rm(fr'[Rr]ipple',                                         fr"When you cast this spell, you may reveal the top \d+ cards of your library. You may cast spells with the same name as this spell from among those cards without paying their mana costs. Put the rest on the bottom of your library"),
    rm(fr'[Ss]cavenge',                                       fr"(?:{MTG_SYMBOL_REGEX})+, Exile this card from your graveyard: Put a number of \+1\/\+1 counters equal to this card's power on target creature. Scavenge only as a sorcery"),
    rm(fr'[Ss]cry',                                           r"(?:To scry \d+, l|L)ook at the top(?: \d+)? cards? of your library(?:, then(?: you may)?|. You may) put (?:any number of them|that card) on the bottom of your library(?: and the rest on top in any order)?"),
    rm(fr'[Ss]hadow',                                         r"(?:This creature|This|It|You|They) can block or be blocked by only creatures with shadow"),
    rm(fr'[Ss]hield',                                         r"If it would be dealt damage or destroyed, remove a shield counter from it instead"),
    rm(fr'[Ss]hroud',                                         r"(?:\{S\} can be paid with 1 mana from a snow source. )?(?:This \w+|This|It|You|They|A \w+ with shroud) can't be the targets? of spells or abilities"),
    rm(fr'[Ss]kulk',                                          r"(?:This creature|This|It|You|They) can't be blocked by creatures with greater power"),
    rm(fr'[Ss]oulbond',                                       r"You may pair this creature with another unpaired creature when either enters the battlefield. They remain paired for as long as you control both of them"),
    rm(fr'[Ss]oulshift',                                      fr"When this creature dies, you may return target Spirit card with mana value \d+ or less from your graveyard to your hand"),
    rm(fr'[Ss]pectacle',                                      r"You may cast this spell for its spectacle cost rather than its mana cost if an opponent lost life this turn"),
    rm(fr'[Ss]plice onto Arcane',                             r"As you cast an Arcane spell, you may reveal this card from your hand and pay its splice cost. If you do, add this card's effects to that spell"),
    rm(fr'[Ss]plit second',                                   r"As long as this spell is on the stack, players can't cast spells or activate abilities that aren't mana abilities"),
    rm(fr'[Ss]quad',                                          fr"As an additional cost to cast this spell, you may pay (?:{MTG_SYMBOL_REGEX})+ any number of times. When this creature enters the battlefield, create that many tokens that are copies of it"),
    rm(fr'[Ss]torm',                                          r"When you cast this spell, copy it for each spell cast before it this turn(?:\. You may choose new targets for the copies)?"),
    rm(fr'[Ss]unburst',                                       r"(?:This(?: creature)?|It|You) enters the battlefield with a (?:charge|\+1\/\+1) counter on it for each color of mana spent to cast it"),
    rm(fr'[Ss]upport',                                        fr"Put a \+1\/\+1 counter on each of up to (X|\d+)(?: other)? target creatures"),
    rm(fr'[Ss]urge',                                          r"You may cast this spell for its surge cost if you or a teammate has cast another spell this turn"),
    rm(fr'[Ss]urveil',                                        r"(?:To surveil \d+, l|L)ook at the top(?: \d+)? cards? of your library(?:, then|\. You may) put (?:any number of them|that card|it) into your graveyard(?: and the rest on top of your library in any order)?"),
    rm(fr'[Ss]uspend',                                        fr"Rather than cast this card from your hand,(?: you may)? pay (?:{MTG_SYMBOL_REGEX})+ and exile it with (?:a|\d+|X) time counters? on it. At the beginning of your upkeep, remove a time counter. When the last is removed, cast it without paying its mana cost(?:\. It has haste)?"),
    rm(fr'[Ss]tun counter',                                   fr"If a permanent with a stun counter would become untapped, remove 1 from it instead"),
    rm(fr'[Ss]wampcycling',                                   fr"(?:{MTG_SYMBOL_REGEX})+, Discard this card: Search your library for a Swamp card, reveal it, put it into your hand, then shuffle"),
    rm(fr'[Ss]wampwalk',                                      r"(?:They|It|You|This creature) can't be blocked as long as defending player controls a Swamp"),
    rm(fr'[Tt]otem armor',                                    r"If enchanted creature would be destroyed, instead remove all damage from it and destroy this Aura"),
    rm(fr'[Tt]raining',                                       r"Whenever this creature attacks with another creature with greater power, put a \+1/\+1 counter on this creature"),
    rm(fr'[Tt]rample',                                        r"(?:This creature|A creature with trample|This|It|You|They) can deal excess combat damage to the player or planeswalker (?:they're|it's) attacking"),
    rm(fr'[Tt]ransmute',                                      fr"(?:{MTG_SYMBOL_REGEX})+, Discard this card: Search your library for a card with the same mana value as this card, reveal it, put it into your hand, then shuffle. Transmute only as a sorcery"),
    rm(fr'[Tt]reasure token',                                 r"(?:It's|They're)(?: an)? artifacts? with \"\{T\}, Sacrifice this artifact: Add 1 mana of any color\.?\""),
    rm(fr'[Tt]ribute',                                        fr"As this creature enters the battlefield, an opponent of your choice may put \d+ \+1\/\+1 counters on it"),
    rm(fr'[Uu]ndaunted',                                      fr"This spell costs (?:{MTG_SYMBOL_REGEX})+ less to cast for each opponent"),
    rm(fr'[Uu]ndying',                                        r"When this creature dies, if it had no \+1\/\+1 counters on it, return it to the battlefield under its owner's control with a \+1\/\+1 counter on it"),
    rm(fr'[Uu]nearth',                                        fr"(?:{MTG_SYMBOL_REGEX})+: Return this card from your graveyard to the battlefield. It gains haste. Exile it at the beginning of the next end step or if it would leave the battlefield. Unearth only as a sorcery"),
    rm(fr'[Uu]nleash',                                        r"You may have this creature enter the battlefield with a \+1\/\+1 counter on it. It can't block as long as it has a \+1/\+1 counter on it"),
    rm(fr'[Vv]anishing',                                      fr"(?:This creature|This|It|You|They) enters the battlefield with (?:a|\d+) time counters? on it. At the beginning of your upkeep, remove a time counter from it. When the last is removed, sacrifice it"),
    rm(fr'[Vv]enture into the dungeon',                       r"Enter the first room or advance to the next room"),
    rm(fr'[Vv]igilance',                                      r"Attacking doesn't cause (it|this creature|them) to tap"),
    rm(fr'[Ww]ard',                                           fr"Whenever (?:equipped|this) creature becomes the target of a spell or ability an opponent controls, counter it unless that player pays (?:\d+ life|(?:{MTG_SYMBOL_REGEX})+)"),
    rm(fr'[Ww]ither',                                         r"(?:This creature|This|It|You|They|A source with wither) deals? damage to creatures in the form of \-1\/\-1 counters"),
    rm(fr'loses all other card types',                        r"It still has its abilities, but it's no longer a \w+"),
    rm(fr'phases out',                                        fr"Auras and Equipment phase out with it. While permanents are phased out, they're treated as though they don't exist"),
    rm(fr'phases out',                                        fr"It phases in or out before its controller untaps during each of their untap steps. While it's phased out, it's treated as though it doesn't exist"),
    rm(fr'phases out',                                        fr"Treat it and anything attached to it as though they don't exist until its controller's next turn"),
    rm(fr'phases out',                                        fr"While (?:they're|it's) phased out, (?:they're|it's) treated as though (?:they|it) doe?s?n't exist. (?:They|It|Each 1) phases? in before (?:that player|you|its controller) untaps? during (?:their|your) next untap step"),
]
REMINDER_REGEX = '|'.join(['(?:' + x.reminder + ')' for x in MTG_REMINDER_TEXT])
REMINDER_REGEX = fr"\((?:{REMINDER_REGEX})(?:(?:[ ,\.]|and)*(?:{REMINDER_REGEX}))*\.?\)"

