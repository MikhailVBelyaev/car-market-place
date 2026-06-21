
log (check_file(pathToConfig1))
log (check_file(pathToData1))
method()


void aggregation_logic(data as DataFrame, param as String) as DataFrame {


}

void method(pathToConfig1: String, … pathToData1: String, …){
//conf = readConfig(pathToConfig1, ...)
 for each param in conf.params {
    log
//data = readData(pathToData1, ...)
 
//complex aggregation logic
data = aggregation_logic(data, param)

//get staitistics for aggregated data and save it
 
//write data to sink1 
//write data to sink2
 
}