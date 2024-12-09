
CREATE TABLE IF NOT EXISTS `Batch` (
    `BatchId` INTEGER NOT NULL PRIMARY KEY autoincrement
    ,StartDate text
    ,EndDate text
    ,IsSuccessful integer
    ,Comment text
    ,CreatedOn text not null default 'CURRENT_TIMESTAMP'
);

CREATE TABLE IF NOT EXISTS `SearchResult` (
    `SearchResultId` integer  not null primary  key autoincrement
    ,`BatchId` integer
    ,`Name` text
    ,`Url` text
    ,`Timestamp` text
    ,`Metadata` text
    ,`Price` integer
    ,`CreatedOnDate` text not null default 'CURRENT_TIMESTAMP'
    ,FOREIGN KEY (BatchId) REFERENCES Batch(BatchId)
);


CREATE TABLE IF NOT EXISTS `Errors` (
    `ErrorsId` integer  not null primary key autoincrement
    ,`BatchId` integer
    ,`SearchResultId` integer references SearchResult(SearchResultId)
    ,`Description` text
    ,`CreatedOnDate` text not null default  'CURRENT_TIMESTAMP'
    ,FOREIGN KEY (BatchId) REFERENCES Batch(BatchId)
    ,FOREIGN KEY (SearchResultId) REFERENCES SearchResult(SearchResultId)
);
