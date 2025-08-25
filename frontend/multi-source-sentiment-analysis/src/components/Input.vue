<template>
  <button @click="triggerAction" class="my-button">Submit</button>
  <input type="text" v-model="target" @keyup.enter="triggerAction" placeholder="Enter text here" class="my-input" />
</template>
  
<script>
  export default {
    data() {
      return {
        target: ''
      };
    },
    methods: {
      triggerAction() {
        this.$emit('data-sent', this.target);
        this.$emit('button-clicked'); // Emit a custom event
      }
    }
  }
</script>

<style scoped>
.my-button {
  margin-right: 5px;
  height: 30px;
}
.my-input {
  height: 30px;
  width: 240px;
}
</style>