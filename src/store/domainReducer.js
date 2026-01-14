const defaultState = {
  domain: "",
  scan_id: "",
  ulinks: {},
  slaves: {},
  finished: false,
}

export const domainReducer = (state = defaultState, action) => {
  switch (action.type) {
    case "SET_DOMAIN":
      return {...state, domain: action.payload}
    case "SET_SCAN_ID":
      return {...state, scan_id: action.payload}
    case "SET_ULINKS":
      return {...state, ulinks: action.payload}
    case "SET_SLAVES":
      return {...state, slaves: action.payload}
    case "SET_FINISHED":
      return {...state, finished: action.payload}
    
    default:
      return state
  }
}