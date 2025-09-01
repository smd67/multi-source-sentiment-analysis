<template>
  <header>
    <div class="wrapper">
      <HelloWorld msg="Stock Analyzer" />
    </div>
    <img alt="Vue logo" class="logo" src="./assets/multi-source-sentiment-analysis.jpg" width="300" height="300" />
    <div class="input-division">
      <input type="radio" id="single-threaded" value="single-threaded" v-model="selectedOption" name="single-threaded">
      <label for="optionB">Single-thread</label>
      <input type="radio" id="multi-threaded" value="multi-threaded" v-model="selectedOption" name="multi-threaded">
      <label for="optionA">Multi-thread</label>
    </div>
    <div class="spinner" v-if="isLoading"></div>
    <div class="input-division">
      <Input @button-clicked="fetchData" @data-sent="handleData"/>
    </div>
  </header>

  <main>
    <Display :logoData="logoData" :description="description" :stockInfo="stockInfo" :stockDataLabels="stockDataLabels" :stockDataValues="stockDataValues" :youtubeSentiment="youtubeSentiment" :redditSentiment="redditSentiment" />
  </main>
</template>

<script>
import HelloWorld from './components/HelloWorld.vue'
import Display from './components/Display.vue';
import Input from './components/Input.vue';
import axios from 'axios';

export default {
    components: { HelloWorld, Display, Input },
    data() {
      return {
        logoData: [], // This array will store the fetched data
        description: '',
        stockInfo: {},
        target: '',
        isLoading: false,
        selectedOption: "single-threaded",
        stockDataLabels: [],
        stockDataValues: [],
        youtubeSentiment: -1.0,
        redditSentiment: -1.0,
      };
    },
    methods: {
      handleData(data) {
        this.target = data;
      },

      getLogo() {
        return(this.logoData[0].url);
      },
      async fetchData() {
        if(this.selectedOption == "multi-threaded"){
          this.fetchDataMultiThreaded();
        } else {
          this.fetchDataSingleThreaded();
        }
      },
      async fetchDataSingleThreaded() {
        var apiUrl = 'http://127.0.0.1:8005/get-logo/'; // Replace with your actual API endpoint
        const config = {
            headers: {
                'Content-Type': 'application/json'
            }
        };
        const requestBody = {
            target: this.target
        }
        let startTime = Date.now();
        try {
          this.isLoading = true;
          var response = await axios.post(apiUrl, requestBody, config);
          this.logoData = response.data; // Assign the fetched data to tableData

          apiUrl = 'http://127.0.0.1:8005/get-description/';
          response = await axios.post(apiUrl, requestBody, config);
          this.description = response.data.text;

          apiUrl = 'http://127.0.0.1:8005/get-stock-info/';
          response = await axios.post(apiUrl, requestBody, config);
          this.stockInfo = response.data;

          apiUrl = 'http://127.0.0.1:8005/get-stock-data/';
          response = await axios.post(apiUrl, requestBody, config);
          this.stockDataLabels = response.data.map(obj => obj.month);
          this.stockDataValues = response.data.map(obj => obj.price);

          apiUrl = 'http://127.0.0.1:8005/get-youtube-sentiment/';
          response = await axios.post(apiUrl, requestBody, config);
          this.youtubeSentiment = response.data.score;
          
          apiUrl = 'http://127.0.0.1:8005/get-reddit-sentiment/';
          response = await axios.post(apiUrl, requestBody, config);
          this.redditSentiment = response.data.score;
          console.log(this.redditSentiment);
          
        } catch (error) {
          console.error('Error fetching data:', error);
        } finally {
          this.isLoading = false;
          let endTime = Date.now();
          let elapsedTime = endTime - startTime; // Elapsed time in milliseconds
          console.log(`Elapsed time for ${this.selectedOption}: ${elapsedTime} ms`);
        }
    },
    async fetchDataMultiThreaded() {
        var apiUrl = 'http://127.0.0.1:8005/get-all-data/'; 
        const config = {
            headers: {
                'Content-Type': 'application/json'
            }
        };
        const requestBody = {
            target: this.target
        }
        let startTime = Date.now();
        try {   
          this.isLoading = true;
          var response = await axios.post(apiUrl, requestBody, config);
          this.logoData = response.data.logo; // Assign the fetched data to tableData
          this.description = response.data.description.text;
          this.stockInfo = response.data.stock_info;
          var stockData = response.data.stock_data;
          this.stockDataLabels = stockData.map(obj => obj.month);
          this.stockDataValues = stockData.map(obj => obj.price);
          this.youtubeSentiment = response.data.youtube_sentiment.score;
          this.redditSentiment = response.data.reddit_sentiment.score;
        } catch (error) {
          console.error('Error fetching data:', error);
        } finally {
          this.isLoading = false;
          let endTime = Date.now();
          let elapsedTime = endTime - startTime; // Elapsed time in milliseconds
          console.log(`Elapsed time for ${this.selectedOption}: ${elapsedTime} ms`);
        }
    },
  },
};
</script>

<style scoped>
header {
  line-height: 1.5;
}

.logo {
  display: block;
  margin: 0 auto 2rem;
  border: 0.5px dotted navy;
}

@media (min-width: 1024px) {
  header {
    align-items: flex-start;
    justify-content: flex-start;
    padding-right: calc(var(--section-gap) / 2);
  }

  .logo {
    margin: 0 2rem 0 0;
  }

  header .wrapper {
    display: flex;
    place-items: flex-start;
    flex-wrap: wrap;
    margin-top: 10px;
  }
}
.spinner {
  border: 4px solid rgba(0, 0, 0, 0.1);
  border-left-color: #3498db;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
}
@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.input-division {
  display: flex;
  align-items: center;
  padding-top: 10px;
  padding-bottom: 10px;
  gap: 10px; 
}
</style>
