require 'torch'
require 'hdf5'

local utils = require 'util.utils'

local DataLoader = torch.class('DataLoader')


function DataLoader:__init(kwargs)
  local h5_file = utils.get_kwarg(kwargs, 'input_h5')
  local json_file = utils.get_kwarg(kwargs, 'input_json')
  self.batch_size = utils.get_kwarg(kwargs, 'batch_size')
  self.seq_length = utils.get_kwarg(kwargs, 'seq_length')
  self.rand_mtg_fields = utils.get_kwarg(kwargs, 'rand_mtg_fields')

  self:init_random()

  -- Just slurp all the data into memory
  self.chunks = {}
  local f = hdf5.open(h5_file, 'r')
  self.chunks.train = f:read('/train'):all()
  self.chunks.val = f:read('/val'):all()
  self.chunks.test = f:read('/test'):all()
  self.chunk_delimiter = f:read('/chunk_delimiter'):all()

  if self.rand_mtg_fields == 1 then
    local vocab = utils.read_json(json_file)
    local token_to_idx = {}
    for k, v in pairs(vocab.token_to_idx) do
      token_to_idx[k] = tonumber(v)
    end
    self.mana_open_delimeter = token_to_idx['{']
    self.mana_close_delimeter = token_to_idx['}']
    self.mana_unary = token_to_idx['^']
    self.card_sep = token_to_idx['\n']
    self.card_field_sep = token_to_idx['|']
  end

  self.splits = {}
  -- initialize tensors of correct size and data types
  -- to be overridden each time chunk order is randomized
  self.splits.train = f:read('/train_vector'):all()
  self.splits.val = f:read('/val_vector'):all()
  self.splits.test = f:read('/test_vector'):all()

  self.x_splits = {}
  self.y_splits = {}
  self.split_sizes = {}
  for split, _ in pairs(self.chunks) do
    self:fix_chunk_indexing(split)  -- only called during init
    self:setXYSplits(split)  -- called many times
  end

  self.split_idxs = {train=1, val=1, test=1}
end


function DataLoader:init_random()
  -- call random a few times to mitigate the well-known not-so-random lua issue
  math.randomseed(os.time())
  for _ = 1, 100 do
    math.random()
  end
end


function DataLoader:fix_chunk_indexing(split)
  -- hdf5 group objects are indexed by strings
  -- convert these strings into numbers, which the preprocessor guarantees
  local new_chunks = {}
  for k, v in pairs(self.chunks[split]) do
    new_chunks[tonumber(k)] = v
  end
  self.chunks[split] = new_chunks
end


function DataLoader:len(x)
  -- returns number of elements in table x, regardless of key types
  -- Does not work for tensors, which have a builtin size function
  n = 0
  for _, _ in pairs(x) do
    n = n + 1
  end
  return n
end


function DataLoader:shuffle_list(x)
  -- shuffles a table in place via the Fisher–Yates algorithm
  -- assumes keys are contiguous positive integers begining at 1
  for i = self:len(x), 2, -1 do
    local j = math.random(i)
    x[i], x[j] = x[j], x[i]
  end
end


function DataLoader:shuffle_mtg_mana_cost(s, start, stop)
  -- shuffles in place the order of unordered mana cost strings
  --  s is a linear tensor of encoded characters
  --  start and stop indicate the first and last index of the mana cost substring
  -- mana costs consist of arbitrary character pairs, and unary counters
  --  Counters are always a single carret "^", which we use to distinguish character pairs
  -- The character pairs must stay together as an atomic substring
  -- All character pairs and unary counters are then shuffled and rewritten in place

  -- copy data segment from s to create a static reference
  local s_clone = s:sub(start, stop):clone()
  local atomic_substrings = {}
  local i_substring = 1

  -- partition all characters into atomic_substrings, either one or two characters at a time 
  local i_char = 1
  while i_char <= (stop - start + 1) do
    if s_clone[{i_char}] == self.mana_unary then
      atomic_substrings[i_substring] = s_clone:sub(i_char, i_char)
      i_char = i_char + 1
      i_substring = i_substring + 1

    else
      atomic_substrings[i_substring] = s_clone:sub(i_char, i_char + 1)
      i_char = i_char + 2
      i_substring = i_substring + 1
    end
  end

  local len_atomic_substrings = i_substring - 1

  -- shuffle substrings
  self:shuffle_list(atomic_substrings)

  -- write shuffled substrings to original data
  i_char = start
  for i_substring = 1, len_atomic_substrings do
    for i_substring_char = 1, atomic_substrings[i_substring]:size(1) do
      s[{i_char}] = atomic_substrings[i_substring][i_substring_char]
      i_char = i_char + 1
    end
  end

end


function DataLoader:shuffle_mtg_card_fields(s, start, stop)
  -- shuffles in place the order of unordered mtg card fields
  --  s is a linear tensor of encoded characters
  --  start and stop indicate the first and last index of the fields to be shuffled
  --  ending with a field sep delimeter, but not beginning with one
  -- fields consist of arbitrary characters, not including the reserved field sep character

  -- copy data segment from s to create a static reference
  local s_clone = s:sub(start, stop):clone()
  local substrings = {}
  local i_substring = 1

  -- partition all characters into substrings, including the field sep character to the right of each field, but not left
  local field_start = 1  -- opening character guaranteed to be a field character (or ending separator in case of empty field)
  for i_char = 1, (stop - start + 1) do
    if i_char == (stop - start + 1) then
      assert(s_clone[{i_char}] == self.card_field_sep)
    end
    if s_clone[{i_char}] == self.card_field_sep then
      substrings[i_substring] = s_clone:sub(field_start, i_char)
      i_substring = i_substring + 1
      field_start = i_char + 1
    end
  end

  local len_substrings = i_substring - 1

  -- shuffle substrings
  self:shuffle_list(substrings)

  -- write shuffled substrings to original data
  local i_char = start
  for i_substring = 1, len_substrings do
    for i_substring_char = 1, substrings[i_substring]:size(1) do
      s[{i_char}] = substrings[i_substring][i_substring_char]
      i_char = i_char + 1
    end
  end

end


function DataLoader:concat_chunks(split)
  -- concatenates chunks into unified tensor
  i_split = 1
  n_delimeter = self.chunk_delimiter:size(1)

  for i_chunk = 1, self:len(self.chunks[split]) do
    -- add delimeter
    if i_chunk ~= 1 then
      for i_delimeter = 1, n_delimeter do
        self.splits[split][{{i_split, i_split}}] = self.chunk_delimiter[i_delimeter]
        i_split = i_split + 1
      end
    end

    -- copy chunk data
    for i_val = 1, self.chunks[split][i_chunk]:size(1) do
      self.splits[split][{{i_split, i_split}}] = self.chunks[split][i_chunk][i_val]
      i_split = i_split + 1
    end
  end
end


function DataLoader:process_chunks(split)
  -- creates input vector for XY split creation interface
  -- consumes chunked data
  -- randomizes chunk order, and joins into input vector
  -- Optionally randomizes the order of structured content in encoded mtg cards
  --     * symbols in mana costs
  --     * order of unordered fields in a card (eg when the fields are specified by label rather than by order)

  -- randomize chunk order
  self:shuffle_list(self.chunks[split])

  -- concatenate chunks
  self:concat_chunks(split)

  if self.rand_mtg_fields == 1 then
    -- randomize mana cost token order
    -- Parse character stream for mana open/close delimiters
    local delimiter_start = 0  -- 0 is an invalid index
    for i_char = 1, self.splits[split]:size(1) do
      if delimiter_start == 0 then
        if self.splits[split][{i_char}] == self.mana_open_delimeter then
          delimiter_start = i_char
        end
      else
        if self.splits[split][{i_char}] == self.mana_close_delimeter then
          -- shuffle non-empty fields in place
          if i_char - 1 >= delimiter_start + 1 then
            self:shuffle_mtg_mana_cost(self.splits[split], delimiter_start + 1, i_char - 1)
          end
          delimiter_start = 0
        end
      end
    end

    -- randomize mtg card field order, except the first field (card name)
    --  the name field is treated as defining for the rest of the card, and should remain first
    -- Parse character stream for field and card delimeters
    local delimiter_start = 0
    local field_delimeter_count = 0
    for i_char = 1, self.splits[split]:size(1) do
      if self.splits[split][{i_char}] == self.card_sep then
        if field_delimeter_count > 2 then
          self:shuffle_mtg_card_fields(self.splits[split], delimiter_start + 1, i_char - 1)
        end
        delimiter_start = 0
        field_delimeter_count = 0

      elseif self.splits[split][{i_char}] == self.card_field_sep then
        field_delimeter_count = field_delimeter_count + 1
        -- only begin randomization after the first field (name)
        if field_delimeter_count == 2 then
          delimiter_start = i_char
        end
      end
    end

  end
end


function DataLoader:setXYSplits(split)
  self:process_chunks(split)
  local v = self.splits[split]
  local N, T = self.batch_size, self.seq_length

  local num = v:nElement()
  local N_cur = N
  if (N * T > num - 1) then
    N_cur = math.floor((num - 1) / T)
    print(string.format("Not enough %s data, reducing batch size to %d", split, N_cur))
  end
  local extra = num % (N_cur * T)

  -- Ensure that `vy` is non-empty
  if extra == 0 then
    extra = N_cur * T
  end

  -- Chop out the extra bits at the end to make it evenly divide
  local vx = v[{{1, num - extra}}]:view(N_cur, -1, T):transpose(1, 2):clone()
  local vy = v[{{2, num - extra + 1}}]:view(N_cur, -1, T):transpose(1, 2):clone()

  self.x_splits[split] = vx
  self.y_splits[split] = vy
  self.split_sizes[split] = vx:size(1)
end


function DataLoader:nextBatch(split)
  local idx = self.split_idxs[split]
  assert(idx, 'invalid split ' .. split)
  local x = self.x_splits[split][idx]
  local y = self.y_splits[split][idx]

  if idx == self.split_sizes[split] then
    self.split_idxs[split] = 1

    -- reprocess data each epoch
    -- randomizing unordered elements to minimize overtraining
    self:setXYSplits(split)
  else
    self.split_idxs[split] = idx + 1
  end

  return x, y
end

