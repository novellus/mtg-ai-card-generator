require 'torch'
require 'hdf5'

local utils = require 'util.utils'

local DataLoader = torch.class('DataLoader')


function DataLoader:__init(kwargs)
  local h5_file = utils.get_kwarg(kwargs, 'input_h5')
  self.batch_size = utils.get_kwarg(kwargs, 'batch_size')
  self.seq_length = utils.get_kwarg(kwargs, 'seq_length')
  self.rand_mtg_fields = utils.get_kwarg(kwargs, 'rand_mtg_fields')

  -- Just slurp all the data into memory
  self.chunks = {}
  local f = hdf5.open(h5_file, 'r')
  self.chunks.train = f:read('/train'):all()
  self.chunks.val = f:read('/val'):all()
  self.chunks.test = f:read('/test'):all()
  self.chunk_delimiter = f:read('/chunk_delimiter'):all()

  self.splits = {}
  -- initialize tensors of correct size and data types
  -- to be overridden each time chunk order is randomized
  self.splits.train = f:read('/train_vector'):all()
  self.splits.val = f:read('/val_vector'):all()
  self.splits.test = f:read('/test_vector'):all()

  -- -- TODO remove
  -- print('--F--' .. ', self.chunks.test: ' .. tostring(self.chunks.test))
  -- for a, b in pairs(self.chunks.test) do
  --   print('    --G-- ' .. tostring(a) .. ' : ' .. tostring(b))
  -- end
  -- os.exit()

  self.x_splits = {}
  self.y_splits = {}
  self.split_sizes = {}
  for split, _ in pairs(self.chunks) do
    self:fix_chunk_indexing(split)  -- only called during init
    self:setXYSplits(split)  -- called many times
  end

  self.split_idxs = {train=1, val=1, test=1}
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


function DataLoader:shuffle(x)
  -- shuffles a table in place via the Fisher–Yates algorithm
  -- assumes keys are contiguous positive integers begining at 1

  -- TODO use randomseed os time
  -- math.randomseed(os.time)
  math.randomseed(2)
  -- for i=1, 3000 do
  --   print('--R-- ' .. tostring(math.random(i)))
  -- end

  -- -- TODO remove
  -- for a, b in pairs(x) do
  --   print('--T--' .. tostring(a) .. ' : ' .. tostring(b))
  -- end
  local tmp = {}
  local tmp2 = {}
  local tmp3 = 0
  local tmp4 = 0

  -- TODO use self function, remove print
  -- for i = self:len(x), 2, -1 do
  print('--P-- ' .. tostring(#x))
  for i = 2556, 2, -1 do
    -- local j = math.random(i)
    tmp3 = i
    tmp4 = math.random(i)

    -- TODO remove
    -- local j = 7.5
    -- print('--S3-- ' .. tostring(i))
    -- local a = j - 3
    -- print('--S4-- ' .. tostring(a))
    -- tmp[j] = 1
    -- tmp2[i] = 1
    -- tmp[1] = 1
    -- tmp3 = j
    -- tmp4 = i
    -- print('--TMP3.2-- ' .. tostring(tmp3))

    -- x[i], x[j] = x[j], x[i]

    -- -- TODO remove
    -- math.random(i)
    -- math.random(i)
    -- print(tostring(math.random(i)))
    -- print('--S--' .. ', i: ' .. tostring(i) .. ', j: ' .. tostring(j))
    -- print('--S2--' .. ' ' .. tostring(math.random(i)) .. ' ' .. tostring(math.random(i)) .. ' ' .. tostring(math.random(i)) .. ' ' .. tostring(math.random(i)) .. ' ' .. tostring(math.random(i)))
  end

  -- TODO remove
  for a, b in pairs(x) do
    print('--U-- ' .. tostring(a))
  end

  -- TODO remove
  for a, b in pairs(tmp) do
    print('--TMP-- ' .. tostring(a))
  end

  -- TODO remove
  for a, b in pairs(tmp2) do
    print('--TMP2-- ' .. tostring(a))
  end

  -- TODO remove
  print('--TMP3-- ' .. tostring(tmp3))
  print('--TMP4-- ' .. tostring(tmp4))
end


function DataLoader:concat_chunks(split)
  -- concatenates chunks into unified tensor
  i_split = 1

  n_delimeter = self.chunk_delimiter:size(1)

  -- TODO remove
  print('--C--' .. ', split: ' .. tostring(split) .. ', self.splits[split]:size(1): ' .. tostring(self.splits[split]:size(1)))

  for i_chunk = 1, self:len(self.chunks[split]) do
    -- add delimeter
    if i_chunk ~= 1 then
      for i_delimeter = 1, n_delimeter do
        self.splits[split][i_split] = self.chunk_delimiter[i_delimeter]
        i_split = i_split + 1
      end
    end

    -- copy chunk data
    print('--D--' .. ', i_chunk: ' .. tostring(i_chunk))
    print('--D2--' .. ', self:len(self.chunks[split]): ' .. tostring(self:len(self.chunks[split])))
    print('--D3--' .. ', self.chunks[split][i_chunk]: ' .. tostring(self.chunks[split][i_chunk]))
    print('--D4--' .. ', self.chunks[split][i_chunk]:size(1): ' .. tostring(self.chunks[split][i_chunk]:size(1)))
    for i_val = 1, self.chunks[split][i_chunk]:size(1) do
      -- TODO remove
      print('    --B--' .. ', i_val: ' .. tostring(i_val))

      self.splits[split][i_split] = self.chunks[split][i_chunk][i_val]
      i_split = i_split + 1
    end
  end
end


function DataLoader:createV(split)
  -- creates input vector for XY split creation interface
  -- consumes chunked data
  -- randomizes chunk order, and joins into input vector
  -- Optionally randomizes the order of structured content in encoded mtg cards
  --     * symbols in mana costs
  --     * order of unordered fields in a card (eg when the fields are specified by label rather than by order)

  -- TODO remove
  print('--A--')
  print(self.chunks[split][4])
  for a, b in pairs(self.chunks[split]) do
    print('    --A2-- ' .. a)
  end
  -- print(self.chunks[split][1])
  -- print(self.chunks[split][2])
  -- print('--Z-- Exiting...')
  -- os.exit()

  -- randomize chunk order
  self:shuffle(self.chunks[split])

  -- TODO remove
  os.exit()

  -- concatenate chunks
  local v = self:concat_chunks(split)

  -- TODO remove
  print(v[{{1,25}}])
  print('--Y-- Exiting...')
  os.exit()

  -- TODO randomize encoded unordered mtg fields
  if self.rand_mtg_fields == 1 then
  end

  return v
end


function DataLoader:setXYSplits(split)
  local v = self:createV(split)
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

