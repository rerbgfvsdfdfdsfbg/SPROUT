import './styles/search.css'
import { useDispatch, useSelector } from "react-redux";

import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';

export default function Search() {

  const dispatch = useDispatch()
  const domain = useSelector(state => state.domain.domain)

  const updateInput = event => {
    dispatch({type:"SET_DOMAIN", payload:event.target.value})
  }

  const submitInput = event => {
    event.preventDefault() 
    console.log(domain)
    fetch('/api/scan?domain=' + domain + '&max_pages=50&max_depth=2&workers=5&timeout=5')
      .then(res => res.json())
      .then(data => {
        console.log("SCAN ID >> " + data['scan_id'])
        console.log(data['unique_links'])
        dispatch({type:"SET_SLAVES", payload:data['performance']['slave_performance']})
        dispatch({type:"SET_SCAN_ID", payload:data['scan_id']})
        dispatch({type:"SET_ULINKS", payload:data['unique_links']})
        dispatch({type:"SET_FINISHED", payload:true})
      })
  }

  return (
    <div className="search-container">
      <form onSubmit={submitInput}>
        {/* <input onChange={updateInput} id='input'></input> */}
        <TextField fullWidth onChange={updateInput} id='input' label="Domain" type="search" margin="normal"  />
      </form>
    </div>
  );
}