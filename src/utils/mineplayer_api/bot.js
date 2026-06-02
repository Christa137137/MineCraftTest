// bot.js
const mineflayer = require('mineflayer')
const express = require('express')
const app = express()
app.use(express.json())

const bot = mineflayer.createBot({
  host: 'localhost',  
  port: 25566,     
  username: 'testbot', 
  password: '123456',
  version: '1.21.8'
})

// bot.once('login', () => {
//   console.log('Bot login')
// })

// bot.once('spawn', () => {
//   console.log('Bot in the world')
// })

// bot.on('end', () => {
//   console.log('Bot sign out')
// })

bot.on('error', (err) => {
  console.error('Bot error:', err)
})

app.post('/forward', (req, res) => {
  if (!bot.entity) return res.status(500).send({ error: 'Bot not spawn' })

  bot.setControlState('forward', true)

  setTimeout(() => {
    bot.setControlState('forward', false)
  }, 200)

  res.send({ status: 'moved forward' })
})

app.post('/mine/:blockType', async (req, res) => {
  if (!bot.entity) return res.status(500).send({ error: 'Bot not spawn' })

  const blockType = `minecraft:${req.params.blockType}` 

  try {
    const block = bot.findBlock({
      matching: block => block.name === blockType,
      maxDistance: 64
    })

    if (!block) return res.status(404).send({ error: `not found ${blockType} ` })

    await bot.dig(block)
    res.send({ status: 'mined', blockType, position: block.position })
  } catch (err) {
    console.error(err)
    res.status(500).send({ error: err.message })
  }
})

app.post('/chat', (req, res) => {
  const { message } = req.body
  if (!bot.entity) return res.status(500).send({ error: 'Bot 未 spawn' })

  bot.chat(message)
  res.send({ status: 'sent', message })
})

setInterval(() => {}, 1000)

const PORT = 3000
app.listen(PORT, () => {
  // console.log(`MinePlayer API running on http://localhost:${PORT}`)
})
