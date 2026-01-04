import './styles/search.css'
import { useDispatch, useSelector } from "react-redux";

export default function Search() {

  const dispatch = useDispatch()
  const domain = useSelector(state => state.domain.domain)
  let sitemap;

//   useEffect(() => {
//     fetch('/api/getsitemap?q=')
//       .then(res => res.json()) 
//       .then(data => {
//         setCurrentTime(data.time);
//       })
//   }, [])

  const updateInput = event => {
    dispatch({type:"SET_DOMAIN", payload:event.target.value})
  }
  const submitInput = event => {
    event.preventDefault() 
    console.log(domain)
    fetch('/api/scan?domain=' + domain)
      .then(res => res.json())
      .then(data => {
        sitemap = data['sitemap']
        console.log(sitemap)
      })
  }

  return (
    <div className="container">
      <form onSubmit={submitInput}>
        <input onChange={updateInput} id='input'></input>
      </form>
    </div>
  );
}