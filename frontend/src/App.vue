<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import axios from 'axios';
import { Line } from 'vue-chartjs';
import { Chart as ChartJS, Title, Tooltip, Legend, LineElement, CategoryScale, LinearScale, PointElement } from 'chart.js';
import type { Game } from './types/game.ts'

ChartJS.register(Title, Tooltip, Legend, LineElement, CategoryScale, LinearScale, PointElement);

const games = ref<Game[]>([]);
const userId = ref('');
const loading = ref(true);
const syncStatus = ref('');
const lastSynced = ref('');
const apiBaseUrl = '/api';

const fetchGames = async () => {
  loading.value = true;
  try {
    const response = await axios.get(`${apiBaseUrl}/games`);
    games.value = response.data.games;
    lastSynced.value = response.data.last_synced_at;
    userId.value = response.data.user_id;
  } catch (error) {
    console.error('Error fetching games:', error);
  } finally {
    loading.value = false;
  }
};

const syncData = async () => {
  syncStatus.value = 'Syncing...';
  try {
    const response = await axios.post(`${apiBaseUrl}/sync`);
    if (response.data.status === "already_up_to_date") {
      syncStatus.value = 'Archive already up to date!'
    } else if (response.data.status === "no_ids_found") {
      syncStatus.value = 'No puzzle IDs found.'
    } else if (response.data.added === 0) {
      syncStatus.value = 'Sync executed, no new puzzles added.'
    } else {
      syncStatus.value = `Sync successful! Added ${response.data.added} new puzzle records. Fetching new data...`;
      await fetchGames();
    }
  } catch (error) {
    console.error('Error syncing data:', error);
    syncStatus.value = `Sync failed: ${error.message}`;
  }
};

const totalGames = computed(() => games.value.length);

const winningGames = computed(() => 
  games.value.filter(game => game.game_data.status === 'WIN')
);
const totalWins = computed(() => winningGames.value.length);

const winPercentage = computed(() => {
  if (totalGames.value === 0) return '0.00%';
  const percentage = (totalWins.value / totalGames.value) * 100;
  return `${percentage.toFixed(2)}%`;
});

const averageTurns = computed(() => {
  if (totalWins.value === 0) return 'N/A';
  
  const totalTurns = winningGames.value.reduce((sum, game) => {
    return sum + game.game_data.currentRowIndex;
  }, 0);
  
  const average = totalTurns / totalWins.value;
  return average.toFixed(2);
});

const chartData = computed(() => {
  const sortedGames = [...games.value].reverse();
  
  const finishedGames = sortedGames.filter(game => 
    game.game_data.status === 'WIN' || game.game_data.status === 'FAIL'
  );

  let lastMonth = null;
  
  const labels = finishedGames.map(game => {
    const date = new Date(game.print_date);
    const currentMonth = date.getMonth();

    if (currentMonth !== lastMonth) {
      lastMonth = currentMonth;
      return date.toLocaleString('default', { month: 'short', year: 'numeric' });
    }
    return '';
  });

  const allPrintDates = finishedGames.map(game => game.print_date);
  const allSolutions = finishedGames.map(game => game.solution);
  
  return {
    labels: labels,
    datasets: [
      {
        label: 'Guesses',
        backgroundColor: '#41B883',
        borderColor: '#41B883',
        data: finishedGames.map(game => 
          game.game_data.status === 'WIN' 
            ? game.game_data.currentRowIndex
            : 7
        ),
        tension: 0.3,
        printDates: allPrintDates,
        solutions: allSolutions,
      }
    ]
  };
});

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    y: {
      min: 1,
      max: 7,
      ticks: {
        stepSize: 1,
        callback: function(value) {
          return value === 7 ? 'FAIL' : value;
        }
      },
      title: {
        display: true,
        text: 'Number of Guesses'
      }
    },
    x: {
      title: {
        display: true,
        text: 'Date'
      },
      ticks: {
        autoSkip: false,
        maxRotation: 45,
        minRotation: 45,
        callback: function(val, index) {
          return this.getLabelForValue(val) !== '' ? this.getLabelForValue(val) : null;
        }
      },
      grid: {
        drawOnChartArea: true,
        color: (context) => {
          const label = context.chart.data.labels[context.tick.value];
          return label !== '' ? 'rgba(0, 0, 0, 0.1)' : 'rgba(0, 0, 0, 0.0)';
        }
      }
    }
  },
  plugins: {
    tooltip: {
      displayColors: false,
      callbacks: {
        title: function(context) {
          const dataIndex = context[0].dataIndex;
          const printDate = context[0].dataset.printDates[dataIndex];
          return printDate
        },
        label: function(context) {
          let label = context.dataset.label || '';
          if (label) {
            label += ': ';
          }
          if (context.parsed.y === 7) {
            label += 'FAIL (6/6 attempts)';
          } else {
            label += context.parsed.y;
          }
          const dataIndex = context.dataIndex;
          const solution = context.dataset.solutions[dataIndex];

          return [
            label,
            `${solution}`
          ];
        },
      }
    }
  }
};

const getTurns = (game) => {
  return game.game_data.currentRowIndex;
};

const getWordleUrl = (dateStr) => {
  return `https://www.nytimes.com/games/wordle/${dateStr}`;
};

const downloadGames = () => {
  const json = JSON.stringify(games.value, null, 2);
  const blob = new Blob([json], { type: "application/json" });
  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = "wordle_games.json";
  a.click();

  URL.revokeObjectURL(url);
};

onMounted(() => {
  fetchGames();
  document.title = "Wordle Stats Archive"
});
</script>

<template>
  <div class="wordle-stats">
    <h1>Wordle Stats Dashboard</h1>
    
    <div class="userinfo">
      <p>
        User ID:
        {{ userId }}
      </p>
      <p>
        Last contentful sync:
        {{ lastSynced ? (isNaN(Date.parse(lastSynced)) ? lastSynced : new Date(lastSynced).toUTCString()) : 'Never' }}
      </p>
    </div>
    <button @click="syncData" :disabled="syncStatus === 'Syncing...'" class="sync-button">
      {{ syncStatus === 'Syncing...' ? 'Syncing...' : 'Sync Archive Data' }}
    </button>
    <p v-if="syncStatus && syncStatus !== 'Syncing...'" class="sync-message">{{ syncStatus }}</p>

    <div v-if="loading" class="loading-message">
      Loading game data...
    </div>

    <div v-else-if="games.length === 0" class="no-data-message">
      No games found for user ID: **{{ userId }}**. Please sync your data.
    </div>

    <div v-else>
      <section class="stats-summary">
        <div class="header">
          <h2>📊 Overall Statistics</h2>
        </div>
        <div class="stat-cards">
          <div class="card">
            <h3>Total Games Played</h3>
            <p>{{ totalGames }}</p>
          </div>
          <div class="card">
            <h3>Win Percentage</h3>
            <p>{{ winPercentage }}</p>
          </div>
          <div class="card">
            <h3>Average Turns (Wins Only)</h3>
            <p>{{ averageTurns }}</p>
          </div>
        </div>
      </section>

      <hr>

      <section class="guess-chart">
        <div class="header">
          <h2>📈 Guess Progression Over Time</h2>
        </div>
        <div class="chart-container">
          <Line :data="chartData" :options="chartOptions" :key="games.length" />
        </div>
      </section>

      <hr>

      <section class="games-list">
        <div class="header">
          <h2>🗓️ Game History</h2>
          <button @click="downloadGames" class="download-button">
            Download JSON
          </button>
        </div>
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Turns</th>
              <th>Result</th>
              <th>Solution</th>
              <th>Link</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="game in games" :key="game._id.toString()">
              <td>{{ game.print_date }}</td>
              <td>
                <span v-if="game.game_data.status === 'WIN'">{{ getTurns(game) }}/6</span>
                <span v-else-if="game.game_data.status === 'FAIL'">X/6</span>
                <span v-else>N/A</span>
                <span v-if="game.game_data.hardMode">*</span>
              </td>
              <td>
                <span :class="{'win': game.game_data.status === 'WIN', 'fail': game.game_data.status === 'FAIL'}">
                  {{ game.game_data.status }}
                </span>
              </td>
              <td>{{ game.solution }}</td>
              <td>
                <a :href="getWordleUrl(game.print_date)" target="_blank" class="wordle-link-button">
                  Go to puzzle
                </a>
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>
  </div>
</template>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #34495e;
  border-bottom: 2px solid #ecf0f1;
  padding-bottom: 10px;
  margin-bottom: 20px;
}

.userinfo {
  display: flex;
  justify-content: space-between;
}

.wordle-stats {
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px;
  font-family: Arial, sans-serif;
}

h1 {
  text-align: center;
  color: #2c3e50;
  margin-bottom: 30px;
}

.sync-button {
  background-color: #4CAF50;
  color: white;
  padding: 10px 20px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 16px;
  margin-bottom: 15px;
  display: block;
  width: 100%;
}

.sync-button:hover:not(:disabled) {
  background-color: #45a049;
}

.sync-button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.sync-message {
  text-align: center;
  font-weight: bold;
  margin-bottom: 20px;
  color: #3498db;
}

hr {
  margin: 40px 0;
  border: 0;
  border-top: 1px solid #eee;
}

.stat-cards {
  display: flex;
  justify-content: space-around;
  gap: 20px;
  text-align: center;
}

.card {
  flex: 1;
  background-color: #f9f9f9;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.card h3 {
  margin-top: 0;
  font-size: 1.1em;
  color: #7f8c8d;
}

.card p {
  font-size: 2.5em;
  font-weight: bold;
  color: #2c3e50;
}

.chart-container {
  height: 400px;
  width: 100%;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
}

th, td {
  border: 1px solid #dddddd;
  text-align: left;
  padding: 12px;
}

th {
  background-color: #f2f2f2;
  font-weight: bold;
  color: #333;
}

tr:nth-child(even) {
  background-color: #f9f9f9;
}

.win {
  color: green;
  font-weight: bold;
}

.fail {
  color: red;
  font-weight: bold;
}

.wordle-link-button {
  display: inline-block;
  background-color: #3498db;
  color: white;
  text-decoration: none;
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 0.9em;
}

.wordle-link-button:hover {
  background-color: #2980b9;
}

.download-button {
  display: block;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  background-color: #4CAF50;
  color: white;
  text-decoration: none;
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 0.9em;
}

.download-button:hover {
  background-color: #45a049;
}

.loading-message, .no-data-message {
    text-align: center;
    padding: 20px;
    font-size: 1.2em;
    color: #95a5a6;
}
</style>