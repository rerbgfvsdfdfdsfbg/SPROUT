import './App.css'
import Header from './components/Header'
import Search from './components/Search'
import Sitemap from './components/Sitemap';
import { store } from "./store";
import { Provider } from 'react-redux'

function App() {

  return (
    <Provider store={store}>
      <Header />
      <Search />
      <Sitemap />
    </Provider>
  )
}

export default App
