<!-- Display.vue -->
<template>
  <div class="my-grid" v-if="description != ''">
    <div class="grid-item">
      <div>
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
      </div>
      <div><img :src="getLogo()" width="150" height="150"/></div>
    </div>
    <div class="grid-item"><p>{{ description }}</p></div>
    <div class="grid-item"><Line :data="getChartData()" :options="getChartOptions()" /></div>
  </div>
</template>

<script>
import Input from './Input.vue';
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
    }
  },
  data() {
  },
  methods: {
    getLogo() {
      return(this.logoData[0].url);
    },
    getChartData() {
      console.log("IN getChartData, labels: " + this.stockDataLabels);
      console.log("IN getChartData, values: " + this.stockDataValues);
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
  grid-template-rows: repeat(2, auto); /* 2 rows, height determined by content */
  gap: 10px; /* Adjust as needed for spacing */
  padding-top: 30px;
  padding-bottom: 10px;
}
.grid-item {
  /* Optional: Add styling for individual grid items */
  border: 1px solid #ccc;
  padding: 10px;
}
</style>