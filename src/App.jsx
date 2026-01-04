import './App.css'
import Header from './components/Header'
import Search from './components/Search'
import { store } from "./store";
import { Provider } from 'react-redux'

function App() {

  return (
    <Provider store={store}>
      <Header />
      <Search />
    </Provider>
  )
}

export default App
