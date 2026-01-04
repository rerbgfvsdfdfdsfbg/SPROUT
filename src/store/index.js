import { combineReducers } from "redux";
import { legacy_createStore as createStore} from 'redux'
import { domainReducer } from "./domainReducer";

const rootReducer = combineReducers({
    domain: domainReducer,
})

export const store = createStore(rootReducer)