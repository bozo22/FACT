import gym
import random
import numpy as np


class Donut(gym.Env):
    def __init__(self, people, episode_length, seed, state_mode="full", p=None, distribution=None, d_param1=None, d_param2=None, zero_memory=False):
        # full: number of donuts for each person so far as a list [d1, d2, ...]
        # compact: full but as one number
        # binary: binary state of full
        # reset: number of donuts for person i - min number of donuts

        self.people = people
        self.seed = seed
        self.episode_length = episode_length
        self.action_space = gym.spaces.Discrete(self.people)
        self.state_mode = state_mode
        self.nsw_lambda = 1e-4
        self.observation_space = gym.spaces.MultiBinary(
            np.power(2, self.people), seed=self.seed
        )
        self.distribution = distribution
        self.d_param1 = d_param1
        self.d_param2 = d_param2
        self.zero_memory = zero_memory

        self.memory_space = gym.spaces.MultiBinary(
            np.power(self.episode_length + 1, self.people), seed=self.seed
        )
        if self.state_mode == "binary":
            self.memory_space = gym.spaces.MultiBinary(
                self.people * int(np.ceil(np.log2(self.episode_length + 1))),
                seed=self.seed,
            )
        elif self.state_mode == "compact":
            ans = np.power(self.episode_length + 1, self.people + 1)
            self.memory_space = gym.spaces.MultiBinary(ans, seed=self.seed)
        elif self.state_mode == "rnn":
            self.observation_space = gym.spaces.MultiBinary(self.people, seed=self.seed)

        self.donuts = [0 for _ in range(people)]
        self.memory = [0 for _ in range(people)]

        self.curr_episode = 0
        self.default_obs = [1 for _ in range(self.people)]
        self.last_obs = self.default_obs

        if p is None:
            
            self.prob = [1.0 for _ in range(self.people)]
            self.stochastic = False
        else:
            self.prob = p
            self.stochastic = True
        self.reset(seed)

    def binary_state(self, s):
        zero_fill = int(np.ceil(np.log2(self.episode_length)))
        ans = ""
        for i in s:
            ans += bin(i)[2:].zfill(zero_fill)

        # print(s, "***", ans)
        int_ans = []
        for t in ans:
            int_ans.append(int(t))
        return int_ans

    def encode(self, s):
        ans = 0
        p = self.episode_length + 1
        curr_p = 1
        for i in range(len(s)):
            ans += s[i] * curr_p
            curr_p *= p
        return ans
    
    def logistic_prob(self, t, t_mid, steepness):
        return 1.0 / (1.0 + np.exp(-steepness * (t - t_mid)))
    
    def bell_prob(self, t, mu, sigma):
        return np.exp(-((t - mu)**2) / (2.0 * sigma**2))
    
    def uniform_interval_prob(self, t, start, end):
        if t >= start and t <= end:
            prob = 1.0
        else:
            prob = 0.0
        return prob

    def nsw_reward(self, obs):
        nsw_reward = 0
        for i in range(len(obs)):
            nsw_reward += np.log(float(obs[i] + 1) + self.nsw_lambda)
        return nsw_reward

    def step(self, action):
        self.curr_episode += 1
        obs = self.last_obs.copy()
        drop = True
        done = (self.curr_episode >= self.episode_length)

        if not self.stochastic:
            drop = False
            self.donuts[action] += 1
            if not self.zero_memory:
                self.memory[action] += 1

        else:
            if self.last_obs[action]:
                drop = False
                self.donuts[action] += 1
                if not self.zero_memory:
                    self.memory[action] += 1

            for i in range(self.people):
                p = random.random()
                if self.distribution == "logistic":
                    self.prob[i] = self.logistic_prob(
                        self.curr_episode,
                        self.d_param1[i], # middle point
                        self.d_param2[i], # steepness
                        )
                elif self.distribution == "bell":
                    self.prob[i] = self.bell_prob(
                        self.curr_episode, 
                        self.d_param1[i], # mean
                        self.d_param2[i], # std
                    )
                elif self.distribution == "uniform-interval":
                    self.prob[i] = self.uniform_interval_prob(
                        self.curr_episode, 
                        self.d_param1[i],  # start
                        self.d_param2[i],  # end
                    )
                if p <= self.prob[i]:
                    obs[i] = 1
                else:
                    obs[i] = 0

        self.last_obs = obs.copy()
        reward = self.nsw_reward(self.donuts.copy())

        obs = self.last_obs
        if drop:
            reward = 0

        out_state = 0
        pr = 1
        for i in range(self.people):
            if obs[i]:
                out_state += pr
            pr *= 2

        out_memory = self.memory.copy()
        if self.state_mode == "compact":
            out_memory = self.encode(self.memory.copy())
        elif self.state_mode == "full":
            out_memory = self.memory.copy()
        elif self.state_mode == "binary":
            out_memory = self.binary_state(self.memory.copy())
            out_state = obs.copy()

        elif self.state_mode == "reset-binary":
            mn = min(self.memory)
            for i in range(self.people):
                self.memory[i] = self.memory[i] - mn
            out_memory = self.binary_state(self.memory.copy())
            out_state = obs.copy()

        elif self.state_mode == "equal-binary":
            mn = min(self.memory)
            mx = max(self.memory)
            if mn == mx:
                self.memory = [0 for _ in range(self.people)]
            out_memory = self.binary_state(self.memory.copy())
            out_state = obs.copy()

        elif self.state_mode == "deep":
            out_memory = self.memory.copy()
            out_state = obs.copy()

        elif self.state_mode == "deep-reset":
            mn = min(self.memory)
            for i in range(self.people):
                self.memory[i] = self.memory[i] - mn
            out_memory = self.memory.copy()
            out_state = obs.copy()

        elif self.state_mode == "reset":
            mn = min(self.memory)
            for i in range(self.people):
                self.memory[i] = self.memory[i] - mn
            out_memory = self.encode(self.memory.copy())
        elif self.state_mode == "equal-reset":
            mn = min(self.memory)
            mx = max(self.memory)
            if mn == mx:
                self.memory = [0 for _ in range(self.people)]
            out_memory = self.encode(self.memory.copy())
        elif self.state_mode == "rnn":
            out_memory = []
            out_state = obs.copy()
            return out_state, reward, done, {}
        else:
            print("Unknown State Mode")
        return out_state, out_memory, reward, done, {}

    def reset(self, seed=None):
        self.donuts = [0 for _ in range(self.people)]
        self.memory = [0 for _ in range(self.people)]
        self.curr_episode = 0

        if seed is not None:
            self.seed = seed
            random.seed(self.seed)

        self.last_obs = self.default_obs
        if self.stochastic:
            for i in range(self.people):
                p = random.random()
                if p <= self.prob[i]:
                    self.last_obs[i] = 1
                else:
                    self.last_obs[i] = 0
        obs = self.last_obs.copy()
        out_state = 0
        pr = 1
        for i in range(self.people):
            if obs[i]:
                out_state += pr
            pr *= 2

        out_memory = self.memory.copy()
        if self.state_mode == "compact":
            out_memory = self.encode(self.memory.copy())
        elif self.state_mode == "full":
            out_memory = self.memory.copy()
        elif self.state_mode == "binary":
            out_memory = self.binary_state(self.memory.copy())
            out_state = obs.copy()

        elif self.state_mode == "reset-binary":
            mn = min(self.memory)
            for i in range(self.people):
                self.memory[i] = self.memory[i] - mn
            out_memory = self.binary_state(self.memory.copy())
            out_state = obs.copy()

        elif self.state_mode == "equal-binary":
            mn = min(self.memory)
            mx = max(self.memory)
            if mn == mx:
                self.memory = [0 for _ in range(self.people)]
            out_memory = self.binary_state(self.memory.copy())
            out_state = obs.copy()

        elif self.state_mode == "deep":
            out_memory = self.memory.copy()
            out_state = obs.copy()

        elif self.state_mode == "deep-reset":
            mn = min(self.memory)
            for i in range(self.people):
                self.memory[i] = self.memory[i] - mn
            out_memory = self.memory.copy()
            out_state = obs.copy()

        elif self.state_mode == "reset":
            mn = min(self.memory)
            for i in range(self.people):
                self.memory[i] = self.memory[i] - mn
            out_memory = self.encode(self.memory.copy())
        elif self.state_mode == "equal-reset":
            mn = min(self.memory)
            mx = max(self.memory)
            if mn == mx:
                self.memory = [0 for _ in range(self.people)]
            out_memory = self.encode(self.memory.copy())
        elif self.state_mode == "rnn":
            out_memory = []
            out_state = obs.copy()
            return out_state
        else:
            print("Unknown State Mode")
        return out_state, out_memory


    