CREATE TABLE IF NOT EXISTS `Batch` (
    `BatchId` INTEGER NOT NULL PRIMARY KEY autoincrement
    ,StartDate text
    ,EndDate text
    ,IsSuccessful integer
    ,Comment text
    ,CreatedOn text not null default 'CURRENT_TIMESTAMP'
);


CREATE TABLE IF NOT EXISTS `Location` (
    `LocationId` integer not null primary key autoincrement
    ,`Latitude` integer
    ,`Longitude` integer
    ,`Line1` text
    ,`Line2` text
    ,`City` text
    ,`State` text
    ,`Zip` text
    ,`Country` text
);

CREATE TABLE IF NOT EXISTS `Product` (
    `ProductId` integer  not null primary  key autoincrement
    ,`BatchId` integer
    ,`LocationId` integer
    ,`Url` text
    ,`Name` text
    ,`Price` integer
    ,`Title` text
    ,`DescriptionBody` text
    ,`BedroomNumber` int
    ,`BathroomNumber` int
    ,`AmountSpaceSquareFt` int
    ,`CraigslistPostDate` text
    ,`IsActive` integer
    ,`CreatedOnDate` text not null default 'CURRENT_TIMESTAMP'
    ,FOREIGN KEY (BatchId) REFERENCES Batch(BatchId)
    ,FOREIGN KEY (LocationId) REFERENCES Location(LocationId)
);