<script setup lang="ts">
// Alias wrapper forwarding to ConnectFormExpandableTextarea
</script>

<template>
  <ConnectFormExpandableTextarea v-bind="$attrs">
    <template v-for="(_, name) in $slots" #[name]="slotProps">
      <slot :name="name" v-bind="slotProps ?? {}" />
    </template>
  </ConnectFormExpandableTextarea>
</template>
