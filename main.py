import random
import numpy as np
import copy
import time
from collections import deque

import torch
import torch.nn as nn
import torch.autograd as autograd

def mini_batch_train(env, agent, max_episodes, max_steps, batch_size):
    episode_rewards = []

    for episode in range(max_episodes):
        state = env.reset()
        episode_reward = 0
        for step in range(max_steps):
            action = agent.get_action(state, episode/max_episodes)
            next_state, reward, done, _ = env.step(action)
            agent.replay_buffer.push(state, action, reward, next_state, done)
            episode_reward += reward

            if len(agent.replay_buffer) > batch_size:
                agent.update(batch_size)

            if done or step == max_steps-1:
                episode_rewards.append(episode_reward)
                if (episode+1) % 100 == 0:
                    avg_score = np.mean(episode_rewards[-100:])
                    print("Episode " + str(episode+1) + ": " + str(avg_score))
                break

            state = next_state

    return episode_rewards

class BasicBuffer:

    def __init__(self, max_size):
        self.max_size = max_size
        self.buffer = deque(maxlen=max_size)

    def push(self, state, action, reward, next_state, done):
        experience = (state, action, np.array([reward]), next_state, done)
        self.buffer.append(experience)

    def sample(self, batch_size):
        state_batch = []
        action_batch = []
        reward_batch = []
        next_state_batch = []
        done_batch = []

        batch = random.sample(self.buffer, batch_size)

        for experience in batch:
            state, action, reward, next_state, done = experience
            state_batch.append(state)
            action_batch.append(action)
            reward_batch.append(reward)
            next_state_batch.append(next_state)
            done_batch.append(done)

        return (state_batch, action_batch, reward_batch, next_state_batch, done_batch)

    def sample_sequence(self, batch_size):
        state_batch = []
        action_batch = []
        reward_batch = []
        next_state_batch = []
        done_batch = []

        min_start = len(self.buffer) - batch_size
        start = np.random.randint(0, min_start)

        for sample in range(start, start + batch_size):
            state, action, reward, next_state, done = self.buffer[start]
            state, action, reward, next_state, done = experience
            state_batch.append(state)
            action_batch.append(action)
            reward_batch.append(reward)
            next_state_batch.append(next_state)
            done_batch.append(done)

        return (state_batch, action_batch, reward_batch, next_state_batch, done_batch)

    def __len__(self):
        return len(self.buffer)

class ConvDQN(nn.Module):

    def __init__(self, input_dim, output_dim):
        super(ConvDQN, self).__init__()
        self.input_dim = (1,1,12,12)#input_dim
        self.output_dim = output_dim


        self.conv = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=4, stride=2),
            nn.ReLU(),
            #nn.Conv2d(32, 64, kernel_size=4, stride=2),
            #nn.ReLU(),
            nn.Conv2d(32, 16, kernel_size=3, stride=1),
            nn.ReLU()
        )

        self.fc_input_dim = self.feature_size()
        self.fc = nn.Sequential(
            nn.Linear(self.fc_input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, self.output_dim)
        )

    def forward(self, state):
        features = self.conv(state)
        features = features.view(features.size(0), -1)
        qvals = self.fc(features)
        return qvals

    def feature_size(self):
        #print(autograd.Variable(torch.zeros(1, *self.input_dim)))

        return self.conv(autograd.Variable(torch.zeros( *self.input_dim))).view(1, -1).size(1)




class DQN(nn.Module):

    def __init__(self, input_dim, output_dim):
        super(DQN, self).__init__()
        self.input_dim = input_dim
        self.output_dim = output_dim

        self.fc = nn.Sequential(
            nn.Linear(self.input_dim[0], 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, self.output_dim)
        )

    def forward(self, state):
        qvals = self.fc(state)
        return qvals

class DQNAgent:

    def __init__(self, env, use_conv=True, learning_rate=3e-2, gamma=0.95, buffer_size=10000):
        self.env = env
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.replay_buffer = BasicBuffer(max_size=buffer_size)
        self.device = "cpu"
        if torch.cuda.is_available():
            self.device = "cuda"

        self.use_conv = use_conv
        if self.use_conv:
          self.model = ConvDQN(env.state.shape, env.no_of_actions).to(self.device)
        else:
            self.model = DQN(env.state.shape, env.no_of_actions).to(self.device)

        self.optimizer = torch.optim.Adam(self.model.parameters())
        self.MSE_loss = nn.MSELoss()

    def get_action(self, state, ratio, eps=0.30):
        state = torch.FloatTensor(state).float().unsqueeze(0).to(self.device)
        #print(state)
        qvals = self.model.forward(state)
        action = np.argmax(qvals.cpu().detach().numpy())

        if(np.random.randn() < (1 - ratio)*eps):
            return self.env.sample_action()

        return action

    def compute_loss(self, batch):
        states, actions, rewards, next_states, dones = batch
        states = torch.FloatTensor(states).to(self.device)
        actions = torch.LongTensor(actions).to(self.device)
        rewards = torch.FloatTensor(rewards).to(self.device)
        next_states = torch.FloatTensor(next_states).to(self.device)
        dones = torch.FloatTensor(dones)

        curr_Q = self.model.forward(states).gather(1, actions.unsqueeze(1))
        curr_Q = curr_Q.squeeze(1)
        next_Q = self.model.forward(next_states)
        max_next_Q = torch.max(next_Q, 1)[0]
        expected_Q = rewards.squeeze(1) + self.gamma * max_next_Q

        loss = self.MSE_loss(curr_Q, expected_Q)
        return loss

    def update(self, batch_size):
        batch = self.replay_buffer.sample(batch_size)
        loss = self.compute_loss(batch)

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

import Grid
import Policy
import Simulate



class game_env():
  def __init__(self):
    self.reset()

  def sample_action(self):
    #return random.randint(0,self.sim_obj.policy.no_of_actions-1)
    return random.choice(self.sim_obj.policy.valid_actions)

  def reset(self):
    def p_standard(p):
        def p_fn(day,global_state,a1,nbrs):  #probability of going from immune to susceptible.
          return p
        return p_fn

    def p_infection(day,global_state,my_agent,neighbour_agents):  # probability of infectiong neighbour
        p_inf=0.3
        p_not_inf=1
        for nbr_agent in neighbour_agents:
            if nbr_agent.individual_type in ['Infected','Asymptomatic'] and not nbr_agent.policy_state['quarantined']:
                p_not_inf*=(1-p_inf)

        return 1 - p_not_inf

    individual_types=['Susceptible','Infected','Immune','Vaccinated']
    color_list=['white', 'black','red','blue']
    gridtable =np.zeros((12,12))
    gridtable[5][5]=1
    gridtable[2][2]=1
    gridtable[7][2]=1
    grid=Grid.Grid(gridtable,individual_types)
    policy=Policy.Vaccinate_block(grid, individual_types,4,0)

    transmission_prob={}
    for t in individual_types:
        transmission_prob[t]={}

    for t1 in individual_types:
        for t2 in individual_types:
            transmission_prob[t1][t2]=p_standard(0)

    transmission_prob['Susceptible']['Infected']= p_infection
    transmission_prob['Infected']['Immune']= p_standard(0.2)
    transmission_prob['Immune']['Susceptible']= p_standard(0)

    self.sim_obj=sim_obj= Simulate.Simulate(transmission_prob,individual_types,grid,policy)
    self.no_of_actions = policy.number_of_actions+1
    self.state=copy.deepcopy(sim_obj.grid.grid)

    return [grid.grid]

  def step(self,action):
    print("Action :", action)
    self.sim_obj.simulate_day(action)
    next_state=copy.deepcopy(self.sim_obj.grid.grid)
    done=False
    reward=0
    # reward = - self.sim_obj.grid.current_types_pop['Infected']
    if self.sim_obj.grid.current_types_pop['Infected']==0:
      done=True
      reward=1

    return [next_state], reward , done, None


MAX_EPISODES = 2000
MAX_STEPS = 4
BATCH_SIZE = 16

env=game_env()
agent = DQNAgent(env, use_conv=True)
episode_rewards = mini_batch_train(env, agent, MAX_EPISODES, MAX_STEPS, BATCH_SIZE)
