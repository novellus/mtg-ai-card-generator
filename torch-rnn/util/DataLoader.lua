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
  self.splits = {}
  local f = hdf5.open(h5_file, 'r')
  self.splits.train = f:read('/train'):all()
  self.splits.val = f:read('/val'):all()
  self.splits.test = f:read('/test'):all()

  self.x_splits = {}
  self.y_splits = {}
  self.split_sizes = {}
  for split, v in pairs(self.splits) do
    self:setXYSplits(split)
  end

  self.split_idxs = {train=1, val=1, test=1}
end


function DataLoader:createV(split)
  -- creates input vector for XY split creation interface
  -- consumes chunked data
  -- randomizes chunk order, and joins into input vector
  -- Optionally randomizes the order of structured content in encoded mtg cards
  --     * symbols in mana costs
  --     * order of unordered fields in a card (eg when the fields are specified by label rather than by order)

  -- TODO
  local v = self.splits[split]

  if rand_mtg_fields == 1 then
    -- TODO
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

