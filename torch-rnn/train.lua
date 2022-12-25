require 'torch'
require 'nn'
require 'optim'

require 'LanguageModel'
require 'util.DataLoader'

local utils = require 'util.utils'
local unpack = unpack or table.unpack

local cmd = torch.CmdLine()

-- Dataset options
cmd:option('-input_h5', 'data/tiny-shakespeare.h5')
cmd:option('-input_json', 'data/tiny-shakespeare.json')
cmd:option('-batch_size', 50)
cmd:option('-seq_length', 50)
cmd:option('-rand_chunks', 0)
cmd:option('-rand_mtg_fields', 0)

-- Model options
cmd:option('-init_from', '')
cmd:option('-reset_iterations', 0)
cmd:option('-reset_learning_rate', 0)
cmd:option('-model_type', 'lstm')
cmd:option('-wordvec_size', 64)
cmd:option('-rnn_size', 128)
cmd:option('-num_layers', 2)
cmd:option('-dropout', 0)
cmd:option('-batchnorm', 0)

-- Optimization options
cmd:option('-max_epochs', 50)
cmd:option('-learning_rate', 2e-3)
cmd:option('-grad_clip', 5)
cmd:option('-lr_decay_every', 1000)
cmd:option('-lr_decay_n_epochs', 1)  -- takes precidence over lr_decay_every if > 0
cmd:option('-lr_decay_factor', 0.5)

-- Output options
cmd:option('-print_every', 1)
cmd:option('-checkpoint_every', 1000)
cmd:option('-checkpoint_n_epochs', 1)  -- takes precidence over checkpoint_every if > 0
cmd:option('-validate_every', 1000)  -- note validation resets the model, so avoid doing this in the middle of an epoch
cmd:option('-validate_n_epochs', 1)  -- takes precidence over validate_every if > 0
cmd:option('-checkpoint_name', 'cv/checkpoint')

-- Benchmark options
cmd:option('-speed_benchmark', 0)
cmd:option('-memory_benchmark', 0)

-- Backend options
cmd:option('-gpu', 0)
cmd:option('-gpu_backend', 'cuda')

local opt = cmd:parse(arg)


-- Set up GPU stuff
local dtype = 'torch.FloatTensor'
if opt.gpu >= 0 and opt.gpu_backend == 'cuda' then
  require 'cutorch'
  require 'cunn'
  cutorch.setDevice(opt.gpu + 1)
  dtype = 'torch.CudaTensor'
  print(string.format('Running with CUDA on GPU %d', opt.gpu))
elseif opt.gpu >= 0 and opt.gpu_backend == 'opencl' then
  -- Memory benchmarking is only supported in CUDA mode
  -- TODO: Time benchmarking is probably wrong in OpenCL mode.
  require 'cltorch'
  require 'clnn'
  cltorch.setDevice(opt.gpu + 1)
  dtype = torch.Tensor():cl():type()
  print(string.format('Running with OpenCL on GPU %d', opt.gpu))
else
  -- Memory benchmarking is only supported in CUDA mode
  opt.memory_benchmark = 0
  print 'Running in CPU mode'
end


-- Initialize the DataLoader and vocabulary
local loader = DataLoader(opt)
local vocab = utils.read_json(opt.input_json)
local idx_to_token = {}
for k, v in pairs(vocab.idx_to_token) do
  idx_to_token[tonumber(k)] = v
end

local num_train = loader.split_sizes['train']
local num_iterations = opt.max_epochs * num_train


-- checkpoint_n_epochs takes precidence over checkpoint_every
-- must be set after the DataLoader is initialized so we know the size of epochs
if opt.checkpoint_n_epochs > 0 then
  opt.checkpoint_every = num_train * opt.checkpoint_n_epochs
end
if opt.validate_n_epochs > 0 then
  opt.validate_every = num_train * opt.validate_n_epochs
end
if opt.lr_decay_n_epochs > 0 then
  opt.lr_decay_every = num_train * opt.lr_decay_n_epochs
end


-- Set up some variables we will use below
local N, T = opt.batch_size, opt.seq_length
local train_loss_history_key = {}  -- encoded as json, which does not support poroper dicts, or the lua json library does not
local train_loss_history_val = {}
local val_loss_history_key = {}
local val_loss_history_val = {}
local learning_rate_history_key = {}
local learning_rate_history_val = {}
local forward_backward_times = {}
local init_memory_usage, memory_usage = nil, {}

local optim_config = {learningRate = opt.learning_rate}

-- Initialize the model and criterion
local opt_clone = torch.deserialize(torch.serialize(opt))
opt_clone.idx_to_token = idx_to_token
local model = nil
local start_i = 0
local start_epoch = 1
if opt.init_from ~= '' then
  print('Initializing from ', opt.init_from)
  local checkpoint = torch.load(opt.init_from)
  model = checkpoint.model:type(dtype)
  train_loss_history_key = checkpoint.train_loss_history_key
  train_loss_history_val = checkpoint.train_loss_history_val
  val_loss_history_key = checkpoint.val_loss_history_key
  val_loss_history_val = checkpoint.val_loss_history_val
  learning_rate_history_key = checkpoint.learning_rate_history_key
  learning_rate_history_val = checkpoint.learning_rate_history_val
  forward_backward_times = checkpoint.forward_backward_times
  memory_usage = checkpoint.memory_usage
  start_epoch = checkpoint.epoch
  if opt.reset_iterations == 0 then
    start_i = checkpoint.i
  end
  if opt.reset_learning_rate == 0 then
    optim_config = {learningRate = checkpoint.learning_rate}
  end
else
  model = nn.LanguageModel(opt_clone):type(dtype)
end
local params, grad_params = model:getParameters()
local crit = nn.CrossEntropyCriterion():type(dtype)

table.insert(learning_rate_history_key, start_epoch)
table.insert(learning_rate_history_val, optim_config.learningRate)
print('Learning rate = ' .. tostring(optim_config.learningRate))

-- print model size
num_params = params:size(1)
model_size_bytes = num_params * 8  -- 64-bit double width floats
model_size_MB = model_size_bytes / (10^6)
print('model has ' .. tostring(num_params) .. ' parameters, totaling ' .. tostring(model_size_MB) .. ' MB')


if opt.memory_benchmark == 1 then
  -- This should only be enabled in GPU mode
  assert(cutorch)
  cutorch.synchronize()
  local free, total = cutorch.getMemoryUsage(cutorch.getDevice())
  init_memory_usage = total - free
end

-- Loss function that we pass to an optim method
local function f(w)
  assert(w == params)
  grad_params:zero()

  -- Get a minibatch and run the model forward, maybe timing it
  local timer
  local x, y = loader:nextBatch('train')
  x, y = x:type(dtype), y:type(dtype)
  if opt.speed_benchmark == 1 then
    if cutorch then cutorch.synchronize() end
    timer = torch.Timer()
  end
  local scores = model:forward(x)

  -- Use the Criterion to compute loss; we need to reshape the scores to be
  -- two-dimensional before doing so. Annoying.
  local scores_view = scores:view(N * T, -1)
  local y_view = y:view(N * T)
  local loss = crit:forward(scores_view, y_view)

  -- Run the Criterion and model backward to compute gradients, maybe timing it
  local grad_scores = crit:backward(scores_view, y_view):view(N, T, -1)
  model:backward(x, grad_scores)
  if timer then
    if cutorch then cutorch.synchronize() end
    local time = timer:time().real
    print('Forward / Backward pass took ', time)
    table.insert(forward_backward_times, time)
  end

  -- Maybe record memory usage
  if opt.memory_benchmark == 1 then
    assert(cutorch)
    if cutorch then cutorch.synchronize() end
    local free, total = cutorch.getMemoryUsage(cutorch.getDevice())
    local memory_used = total - free - init_memory_usage
    local memory_used_mb = memory_used / 1024 / 1024
    print(string.format('Using %dMB of memory', memory_used_mb))
    table.insert(memory_usage, memory_used)
  end

  if opt.grad_clip > 0 then
    grad_params:clamp(-opt.grad_clip, opt.grad_clip)
  end

  return loss, grad_params
end

-- Train the model!
model:training()
for i = start_i + 1, num_iterations do
  local epoch = start_epoch + math.floor((i - start_i) / num_train)
  local float_epoch = start_epoch + (i - start_i) / num_train

  -- Check if we are at the end of an epoch
  if (i - start_i) % num_train == 0 then
    model:resetStates() -- Reset hidden states
  end

  -- Take a gradient step and maybe print
  -- Note that adam returns a singleton array of losses
  local _, loss = optim.adam(f, params, optim_config)
  table.insert(train_loss_history_key, float_epoch)
  table.insert(train_loss_history_val, loss[1])
  if opt.print_every > 0 and (i - start_i) % opt.print_every == 0 then
    local msg = 'Epoch %.2f / %d, i = %d / %d, loss = %f'
    local args = {msg, float_epoch, opt.max_epochs, i, num_iterations, loss[1]}
    print(string.format(unpack(args)))
  end

  -- Maybe run validation
  local validate_every = opt.validate_every
  if (validate_every > 0 and (i - start_i) % validate_every == 0) or i == num_iterations then
    -- Evaluate loss on the validation set. Note that we reset the state of
    -- the model; this might happen in the middle of an epoch, but that
    -- shouldn't cause too much trouble.
    model:evaluate()
    model:resetStates()
    local num_val = loader.split_sizes['val']
    local val_loss = 0
    for j = 1, num_val do
      local xv, yv = loader:nextBatch('val')
      local N_v = xv:size(1)
      xv = xv:type(dtype)
      yv = yv:type(dtype):view(N_v * T)
      local scores = model:forward(xv):view(N_v * T, -1)
      val_loss = val_loss + crit:forward(scores, yv)
    end
    val_loss = val_loss / num_val
    print('val_loss = ', val_loss)
    table.insert(val_loss_history_key, float_epoch)
    table.insert(val_loss_history_val, val_loss)
    model:resetStates()
    model:training()
  end

  -- Maybe save a checkpoint
  local check_every = opt.checkpoint_every
  if (check_every > 0 and (i - start_i) % check_every == 0) or i == num_iterations then
    print('Saving a checkpoint')
    -- First save a JSON checkpoint, excluding the model
    -- TODO save more stats to json file
    local checkpoint = {
      opt = opt,
      train_loss_history_key = train_loss_history_key,
      train_loss_history_val = train_loss_history_val,
      val_loss_history_key = val_loss_history_key,
      val_loss_history_val = val_loss_history_val,
      learning_rate_history_key = learning_rate_history_key,
      learning_rate_history_val = learning_rate_history_val,
      forward_backward_times = forward_backward_times,
      memory_usage = memory_usage,
      learning_rate = optim_config.learningRate,
      i = i,
      epoch = epoch
    }
    local filename = string.format('%s_%f.json', opt.checkpoint_name, float_epoch)
    -- Make sure the output directory exists before we try to write it
    paths.mkdir(paths.dirname(filename))
    utils.write_json(filename, checkpoint)

    -- Now save a torch checkpoint with the model
    -- Cast the model to float before saving so it can be used on CPU
    model:clearState()
    model:float()
    checkpoint.model = model
    local filename = string.format('%s_%f.t7', opt.checkpoint_name, float_epoch)
    paths.mkdir(paths.dirname(filename))
    torch.save(filename, checkpoint)
    model:type(dtype)
    params, grad_params = model:getParameters()
    collectgarbage()
  end

  -- Maybe decay learning rate
  local lr_decay_every = opt.lr_decay_every
  if lr_decay_every > 0 and (i - start_i) % lr_decay_every == 0 then
    local old_lr = optim_config.learningRate

    -- is it ok to not clear the rest of the state when setting a new lr?
    --  optim stores state in config automatically...
    --  *not* clearing state results in much smoother losses, so sticking with that for now
    --  state is cleared on reset tho, so might consider saving state, but it would be the same size as the NN...
    optim_config.learningRate = old_lr * opt.lr_decay_factor
    -- optim_config = {learningRate = old_lr * opt.lr_decay_factor}

    table.insert(learning_rate_history_key, float_epoch)
    table.insert(learning_rate_history_val, optim_config.learningRate)
    print('Learning rate = ' .. tostring(optim_config.learningRate))
  end
end
