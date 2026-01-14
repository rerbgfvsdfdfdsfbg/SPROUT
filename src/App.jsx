import './App.css'
import Header from './components/Header'
import Search from './components/Search'
import Sitemap from './components/Sitemap';
import WorkersList from './components/WorkersList';
import { store } from "./store";
import { Provider } from 'react-redux'

import { useSelector } from "react-redux";

function App() {



  return (
    <Provider store={store}>
      {/* <Header /> */}
      <Search />
      <WorkersList />
      <Sitemap />
    </Provider>
  )
}

export default App
