require 'torch'
require 'nn'

require 'VanillaRNN'
require 'LSTM'

local utils = require 'util.utils'


local LM, parent = torch.class('nn.LanguageModel', 'nn.Module')


function LM:__init(kwargs)
  self.idx_to_token = utils.get_kwarg(kwargs, 'idx_to_token')
  self.token_to_idx = {}
  self.vocab_size = 0
  for idx, token in pairs(self.idx_to_token) do
    self.token_to_idx[token] = idx
    self.vocab_size = self.vocab_size + 1
  end

  self.model_type = utils.get_kwarg(kwargs, 'model_type')
  self.wordvec_dim = utils.get_kwarg(kwargs, 'wordvec_size')
  local rnn_size = utils.get_kwarg(kwargs, 'rnn_size')
  local rnn_sizes = utils.get_kwarg(kwargs, 'rnn_sizes')
  self.num_layers = utils.get_kwarg(kwargs, 'num_layers')
  self.dropout = utils.get_kwarg(kwargs, 'dropout')
  self.batchnorm = utils.get_kwarg(kwargs, 'batchnorm')
  local other = utils.get_kwarg(kwargs, 'other', '')
  if other == '' then other = nil end

  -- preprocess rnn_size per layer
  assert(rnn_size > 0 or rnn_sizes ~= '', 'Must specify either rnn_size or rnn_sizes')
  local _rnn_sizes = {}
  if rnn_sizes ~= '' then
    local i = 1
    for n in string.gmatch(rnn_sizes, "(%d+)") do
      _rnn_sizes[i] = tonumber(n)
      i = i + 1
    end
    assert((i - 1) == self.num_layers, 'rnn_sizes has incorrect number of elements, expected number of layers elements')
  else
    local i = 1
    for i=1, self.num_layers do
      _rnn_sizes[i] = rnn_size
      i = i + 1
    end
  end
  rnn_sizes = _rnn_sizes

  -- Overwrite layer sizes with other sizes if specified
  local other_last_size
  if other ~= nil then
    for i=1, other.num_layers do
      local other_index = i + 1
      if self.dropout > 0 then
        other_index = 2 * i
      end
      local net = other.net:get(other_index)
      local dim = net.hidden_dim
      rnn_sizes[i] = dim
    end
    other_last_size = rnn_sizes[other.num_layers]
  end

  -- local V, D, H = self.vocab_size, self.wordvec_dim, rnn_size
  local V, D = self.vocab_size, self.wordvec_dim

  self.net = nn.Sequential()
  self.rnns = {}
  self.bn_view_in = {}
  self.bn_view_out = {}

  self.net:add(nn.LookupTable(V, D))
  local prev_dim = D
  local H
  for i = 1, self.num_layers do
    H = rnn_sizes[i]

    local other_index
    if other ~= nil then
      other_index = i + 1
      if self.dropout > 0 then
        other_index = 2 * i
      end
    end

    -- Optionally initialize from another supplied model
    local rnn
    if other == nil or i > other.num_layers then
      if self.model_type == 'rnn' then
        rnn = nn.VanillaRNN(prev_dim, H)
      elseif self.model_type == 'lstm' then
        rnn = nn.LSTM(prev_dim, H)
      end
      rnn.remember_states = true
    else
      rnn = other.net:get(other_index)
    end
    table.insert(self.rnns, rnn)
    self.net:add(rnn)

    -- TODO support self.other in this section?
    -- TODO support varying lstm size as well
    if self.batchnorm == 1 then
      local view_in = nn.View(1, 1, -1):setNumInputDims(3)
      table.insert(self.bn_view_in, view_in)
      self.net:add(view_in)
      self.net:add(nn.BatchNormalization(H))
      local view_out = nn.View(1, -1):setNumInputDims(2)
      table.insert(self.bn_view_out, view_out)
      self.net:add(view_out)
    end
    if self.dropout > 0 then
      self.net:add(nn.Dropout(self.dropout))
    end

    prev_dim = H
  end

  for a,b in pairs(self.rnns) do
    print('Layer ' .. a .. ' = ' .. b.input_dim .. ', ' .. b.hidden_dim)
  end

  -- After all the RNNs run, we will have a tensor of shape (N, T, H);
  -- we want to apply a 1D temporal convolution to predict scores for each
  -- vocab element, giving a tensor of shape (N, T, V). Unfortunately
  -- nn.TemporalConvolution is SUPER slow, so instead we will use a pair of
  -- views (N, T, H) -> (NT, H) and (NT, V) -> (N, T, V) with a nn.Linear in
  -- between. Unfortunately N and T can change on every minibatch, so we need
  -- to set them in the forward pass.

  -- Optionally initialize from another supplied model
  if other == nil or other_last_size ~= H then
    self.view1 = nn.View(1, 1, -1):setNumInputDims(3)
    self.view2 = nn.View(1, -1):setNumInputDims(2)
    self.net:add(self.view1)
    self.net:add(nn.Linear(H, V))
    self.net:add(self.view2)
  else
    s = other.net:size()
    self.view1 = other.net:get(s - 2)
    self.view2 = other.net:get(s)
    self.net:add(self.view1)
    self.net:add(other.net:get(s - 1))
    self.net:add(self.view2)
  end
end


function LM:updateOutput(input)
  local N, T = input:size(1), input:size(2)
  self.view1:resetSize(N * T, -1)
  self.view2:resetSize(N, T, -1)

  for _, view_in in ipairs(self.bn_view_in) do
    view_in:resetSize(N * T, -1)
  end
  for _, view_out in ipairs(self.bn_view_out) do
    view_out:resetSize(N, T, -1)
  end

  return self.net:forward(input)
end


function LM:backward(input, gradOutput, scale)
  return self.net:backward(input, gradOutput, scale)
end


function LM:parameters()
  return self.net:parameters()
end


function LM:training()
  self.net:training()
  parent.training(self)
end


function LM:evaluate()
  self.net:evaluate()
  parent.evaluate(self)
end


function LM:resetStates()
  for i, rnn in ipairs(self.rnns) do
    rnn:resetStates()
  end
end


function LM:encode_string(s)
  local l = 0
  for uchar in string.gmatch(s, "([%z\1-\127\194-\244][\128-\191]*)") do
    l = l + 1
  end
  local encoded = torch.LongTensor(l)

  local i = 1
  for token in string.gmatch(s, "([%z\1-\127\194-\244][\128-\191]*)") do
    local idx = self.token_to_idx[token]
    assert(idx ~= nil, 'Got invalid idx')
    encoded[i] = idx
    i = i + 1
  end
  return encoded
end


function LM:decode_string(encoded)
  assert(torch.isTensor(encoded) and encoded:dim() == 1)
  local s = ''
  for i = 1, encoded:size(1) do
    local idx = encoded[i]
    local token = self.idx_to_token[idx]
    s = s .. token
  end
  return s
end


--[[
Sample from the language model. Note that this will reset the states of the
underlying RNNs.

Inputs:
- init: String of length T0
- max_length: Number of characters to sample

Returns:
- sampled: (1, max_length) array of integers, where the first part is init.
--]]
function LM:sample(kwargs)
  local T = utils.get_kwarg(kwargs, 'length', 100)
  local start_text = utils.get_kwarg(kwargs, 'start_text', '')
  local whisper_text = utils.get_kwarg(kwargs, 'whisper_text', '')
  local whisper_every_newline = utils.get_kwarg(kwargs, 'whisper_every_newline', 1)
  local verbose = utils.get_kwarg(kwargs, 'verbose', 0)
  local sample = utils.get_kwarg(kwargs, 'sample', 1)
  local temperature = utils.get_kwarg(kwargs, 'temperature', 1)

  local sampled = torch.LongTensor(1, T)
  self:resetStates()

  -- whispering constants
  local enable_whisper = #whisper_text > 0
  if enable_whisper and verbose > 0 then
    print('Whispering "' .. whisper_text .. '" every ' .. whisper_every_newline .. ' newlines')
  end

  local newline_count = 0
  local encoded_whisper_text = nil
  local s_encoded_whisper_text = nil
  local newline_idx = nil

  -- precompute newline encoding and encoded whisper text
  if enable_whisper then
    newline_idx = self.token_to_idx['\n']
    encoded_whisper_text = self:encode_string(whisper_text):view(1, -1)
    s_encoded_whisper_text = encoded_whisper_text:size(2)
  end

  -- seed start_text
  local scores, first_t
  if #start_text > 0 then
    if verbose > 0 then
      print('Seeding with: "' .. start_text .. '"')
    end
    local x = self:encode_string(start_text):view(1, -1)
    local T0 = x:size(2)
    sampled[{{}, {1, T0}}]:copy(x)
    scores = self:forward(x)[{{}, {T0, T0}}]
    first_t = T0 + 1
  else
    if verbose > 0 then
      print('Seeding with uniform probabilities')
    end
    local w = self.net:get(1).weight
    scores = w.new(1, 1, self.vocab_size):fill(1)
    first_t = 1
  end
  
  -- sample nn
  local _, next_char = nil, nil
  local t = first_t
  while t <= T do
    if sample == 0 then
      _, next_char = scores:max(3)
      next_char = next_char[{{}, {}, 1}]
    else
       local probs = torch.div(scores, temperature):double():exp():squeeze()
       probs:div(torch.sum(probs))
       next_char = torch.multinomial(probs, 1):view(1, 1)
    end
    sampled[{{}, {t, t}}]:copy(next_char)
    scores = self:forward(next_char)
    t = t + 1

    -- whisper mtg card names after two consecutive newlines
    if enable_whisper and t <= T then
      -- check conditions for whispering to begin
      if next_char[{1, 1}] == newline_idx then
        newline_count = newline_count + 1
      else
        newline_count = 0
      end

      if newline_count >= whisper_every_newline then
        -- assume we aren't directly chaining whispers
        newline_count = 0

        -- execute whispering, adjusting the loop counter appropriately
        local sample_chars_remaining = T - t + 1
        if sample_chars_remaining >= s_encoded_whisper_text then
          -- use the whole whisper text (pre-encoded)
          local final_index = t + s_encoded_whisper_text - 1
          sampled[{{}, {t, final_index}}]: copy(encoded_whisper_text)
          scores = self:forward(encoded_whisper_text)[{{}, {s_encoded_whisper_text, s_encoded_whisper_text}}]
          t = t + s_encoded_whisper_text
        else
          -- encode a subset of the whisper text, up to sample length, which will be the end of the sample
          local whisper_substring = whisper_text:sub(1,sample_chars_remaining)
          encoded_whisper_text = self:encode_string(whisper_substring):view(1, -1)
          s_encoded_whisper_text = encoded_whisper_text:size(2)
          local final_index = t + s_encoded_whisper_text - 1
          sampled[{{}, {t, final_index}}]:copy(encoded_whisper_text)
          scores = self:forward(encoded_whisper_text)[{{}, {s_encoded_whisper_text, s_encoded_whisper_text}}]
          t = t + s_encoded_whisper_text
        end
      end
    end
  end

  self:resetStates()
  return self:decode_string(sampled[1])
end


function LM:clearState()
  self.net:clearState()
end
