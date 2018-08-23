import copy

import gym
from gym import spaces
import numpy as np
from gym.utils import seeding


class MDP(object):
    def __init__(self):
        self.state = 0
        self.transition = None
        self.reward = None
        self.terminal = None

    def step(self, action, np_random=np.random):
        raise NotImplementedError()

    def reset(self):
        self.state = 0
        return self.state

    @staticmethod
    def from_config(config, np_random=np.random):
        mode = config.get("mode", None)
        transition = np.array(config.get("transition", []))
        reward = np.array(config.get("reward", []))
        terminal = np.array(config.get("terminal", []))
        if mode == "deterministic":
            mdp = DeterministicMDP(transition, reward, terminal)
        elif mode == "stochastic":
            mdp = StochasticMDP(transition, reward, terminal)
        else:
            raise ValueError("Unknown MDP mode in configuration")
        if config.get("random", False):
            mdp.randomize(np_random)
        return mdp

    def to_config(self):
        raise NotImplementedError()


class DeterministicMDP(MDP):
    def __init__(self, transition, reward, terminal=None):
        """
        :param transition: array of shape S x A
        :param reward: array of shape S x A
        :param terminal: array of shape S
        """
        super(DeterministicMDP, self).__init__()
        self.transition = transition
        self.reward = reward
        self.terminal = terminal
        if terminal is None or not np.size(terminal):
            self.terminal = np.zeros(np.shape(transition)[0])

    def step(self, action, np_random=np.random):
        reward = self.reward[self.state, action]
        done = self.terminal[self.state]
        self.state = self.transition[self.state, action]
        return self.state, reward, done, self.to_config()

    def randomize(self, np_random):
        self.transition = np_random.choice(range(np.shape(self.transition)[0]), size=np.shape(self.transition))
        self.reward = np_random.rand(*np.shape(self.reward))

    def to_config(self):
        return dict(
            mode="deterministic",
            transition=self.transition.tolist(),
            reward=self.reward.tolist(),
            terminal=self.terminal.tolist()
        )

    def update(self, config):
        if "transition" in config:
            self.transition = np.array(config["transition"])
        if "reward" in config:
            self.reward = np.array(config["reward"])
        if "terminal" in config:
            self.terminal = np.array(config["terminal"])


class StochasticMDP(DeterministicMDP):
    def __init__(self, transition, reward, terminal=None):
        """
        :param transition: array of size S x A x S
        :param reward:  array of shape S x A
        :param terminal:  array of shape S
        """
        super(StochasticMDP, self).__init__(transition, reward, terminal)

    def step(self, action, np_random=np.random):
        reward = self.reward[self.state, action]
        probs = self.transition[self.state, action, :]
        done = self.terminal[self.state]
        self.state = np_random.choice(np.arange(np.shape(self.transition)[0]), p=probs)
        return self.state, reward, done, self.to_config()

    @staticmethod
    def from_deterministic(mdp: DeterministicMDP):
        shape = np.shape(mdp.transition)
        new_transition = np.zeros((shape[0], shape[1], shape[0]))
        for s in range(shape[0]):
            for a in range(shape[1]):
                new_transition[s, a, int(mdp.transition[s, a])] = 1
        return StochasticMDP(new_transition, mdp.reward, mdp.terminal)

    def randomize(self, np_random=np.random):
        self.transition = np_random.rand(*np.shape(self.transition))
        self.reward = np_random.rand(*np.shape(self.reward))

    def to_config(self):
        config = super(StochasticMDP, self).to_config()
        config.update(dict(mode="stochastic"))
        return config


class FiniteMDP(gym.Env):
    MAX_STEPS = 10

    def __init__(self):
        # Seeding
        self.np_random = None
        self.seed()

        self.config = FiniteMDP.default_config()
        self.mdp = None
        self.steps = 0
        self.load_config()
        self.reset()

    @staticmethod
    def default_config():
        return dict(mode="deterministic",
                    transition=[[0]],
                    reward=[[0]])

    def configure(self, config):
        self.config.update(config)
        self.load_config()

    def copy_with_config(self, config):
        env_copy = copy.deepcopy(self)
        env_copy.config = config
        env_copy.mdp.update(config)
        return env_copy

    def load_config(self):
        self.mdp = MDP.from_config(self.config, np_random=self.np_random)
        self.observation_space = spaces.Discrete(np.shape(self.mdp.transition)[0])
        self.action_space = spaces.Discrete(np.shape(self.mdp.transition)[1])

    def reset(self):
        self.steps = 0
        return self.mdp.reset()

    def step(self, action):
        state, reward, done, info = self.mdp.step(action, np_random=self.np_random)
        done = done or self.steps > FiniteMDP.MAX_STEPS
        self.steps += 1
        return state, reward, done, info

    def render(self, mode='human'):
        pass

    def seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        return [seed]

