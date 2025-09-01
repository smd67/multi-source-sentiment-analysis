<!-- Display.vue -->
<template>
  <div class="my-grid" v-if="redditSentiment > -1.0">
    <div class="display-grid grid-item">
      <div lass="grid-item">
        <table>
            <thead>
            </thead>
            <tbody>
              <tr>
                  <td>{{ stockInfo.company_name }}</td>
                  <td>{{ stockInfo.ticker_symbol }}</td>
                  <td>{{ stockInfo.stock_price }}</td>
              </tr>
            </tbody>
        </table>
        <img :src="getLogo()" width="150" height="150"/>
      </div>
      <div class="grid-item">
        <p>YouTube Sentiment:</p>
        <div class="progress-bar-container">
          <div class="progress-bar-fill" :style="{ width: youtubeSentiment + '%', 'background-color':  youtubeSentiment <= 50.0 ? 'red' : 'green' }" ></div>
          <span class="progress-value-text">{{ youtubeSentiment.toFixed(2) }}%</span>
        </div>
        <p>Reddit Sentiment:</p>
        <div class="progress-bar-container">
          <div class="progress-bar-fill" :style="{ width: redditSentiment + '%', 'background-color': redditSentiment <= 50.0 ? 'red' : 'green' }"></div>
          <span class="progress-value-text">{{ redditSentiment.toFixed(2) }}%</span>
        </div>
      </div>
    </div>
    <div class="grid-item"><p>{{ description }}</p></div>
    <div class="grid-item"><Line :data="getChartData()" :options="getChartOptions()" /></div>
  </div>
</template>

<script>
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js';
import { Line } from 'vue-chartjs';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

export default {
  name: 'LineChart',
  components: { Line },
  props: {
    description: {
      type: String,
      default: "",
    },
    logoData: {
      type: Array,
      default: () => []
    },
    stockInfo: {
      type: Object,
      default: () => {}
    },
    stockDataLabels: {
      type: Array,
      default: () => []
    },
    stockDataValues: {
      type: Array,
      default: () => []
    },
    youtubeSentiment: {
      type: Number,
      required: true,
      validator: (value) => value >= -1 && value <= 100,
    },
    redditSentiment: {
      type: Number,
      required: true,
      validator: (value) => value >= -1 && value <= 100,
    },
  },
  data() {
  },
  methods: {
    getLogo() {
      return(this.logoData[0].url);
    },
    getChartData() {
      return {
        labels: this.stockDataLabels,
        datasets: [
          {
            label: this.stockInfo.ticker_symbol,
            backgroundColor: '#f87979',
            data: this.stockDataValues,
          },
          // Add more datasets for multiple lines
        ],
      }
    },
    getChartOptions() {
      return {
        responsive: true,
        maintainAspectRatio: false,
        // Add other Chart.js options here (e.g., scales, plugins)
      }
    },
  }
};

</script>

<style scoped>
/* Add basic styling for the table if needed */
table {
  width: 100%;
  border-collapse: collapse;
}
th, td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
}
th {
  background-color: #f2f2f2;
}

.my-grid {
  display: grid;
  grid-template-columns: repeat(1, 1fr); /* 2 columns, equal width */
  grid-template-rows: repeat(3, auto); /* 2 rows, height determined by content */
  gap: 10px; /* Adjust as needed for spacing */
  padding-top: 30px;
  padding-bottom: 10px;
}
.grid-item {
  /* Optional: Add styling for individual grid items */
  border: 1px solid #ccc;
  padding: 5px;
}

.display-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr); /* 2 columns, equal width */
  grid-template-rows: repeat(1, 1fr); /* 2 rows, height determined by content */
  gap: 2px; /* Adjust as needed for spacing */
  padding-top: 1px;
  padding-bottom: 1px;
}

.progress-bar-container {
  width: 100%;
  border-radius: 5px;
  height: 20px; /* Adjust height as needed */
  overflow: hidden; /* Ensures the inner bar stays within bounds */
}

.progress-bar-container {
  position: relative;
  width: 100%;
  height: 20px;
  background-color: #eee;
  border-radius: 10px;
  overflow: hidden; /* Hide overflow of fill */
}

.progress-bar-fill {
  height: 100%;
  background-color: #4caf50; /* Example color */
  border-radius: 10px;
}

.progress-value-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%); /* Center the text */
  color: #333; /* Example color */
  font-weight: bold;
}

</style>